"""LiteLLM + OpenAI (modelo configurável); estruturação e coerência do resultado."""

import json
import logging
import os

import litellm

# Modelo: gpt-4o-mini (mais barato). Override com OPENAI_MODEL no .env
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
logger = logging.getLogger(__name__)


def _build_system_prompt(existing_normalized_names: list[str]) -> str:
    base = """You extract receipt items from OCR text. The text comes from a single GLM-OCR extraction (raw receipt image, no preprocessing). Analyze and output a single list of items.

COHERENCE / INTERPRETABILITY: If the OCR text is too unclear, blurry, empty, or you cannot reliably identify products (e.g. most lines are gibberish, numbers missing, or you would have to guess), you MUST set "interpretation_ok" to false and set "interpretation_message" to a short reason in English (e.g. "Could not interpret: OCR text too blurry or incomplete", "Could not interpret: no product names readable"). Do NOT return guessed items. Only set interpretation_ok true when you can extract at least one clear item from the text.

CRITICAL: List ONLY items that appear clearly in the OCR text. Do NOT invent or assume products. If the text is empty or unreadable, return interpretation_ok: false and interpretation_message explaining why.

AVOID DUPLICATE NORMALIZED NAMES: This user already has the following normalized_name values in their history. You MUST prefer reusing one of these when the product is the same or very similar. Existing normalized names for this user: {existing}

Reply ONLY with valid JSON, no markdown or extra text. When you CAN interpret the receipt, use this format:
{{"interpretation_ok": true, "items": [{{"description": "...", "normalized_name": "...", "quantity": number, "unit": "UNIT|LITER|MILLILITER|KILOGRAM|GRAM", "unit_price": number, "total_value": number}}]}}

When you CANNOT reliably interpret (blurry, empty, unreadable), use:
{{"interpretation_ok": false, "interpretation_message": "Could not interpret: <short reason in English>", "items": []}}

- description: product name exactly as read on the receipt
- normalized_name: generic product name (e.g. "Aveia", "Leite"). PREFER reusing from the existing list above.
- quantity, unit, unit_price, total_value: numbers; unit one of UNIT, LITER, MILLILITER, KILOGRAM, GRAM
If a field cannot be extracted, use null. Include every item you identify on the receipt, and no others."""
    existing_str = ", ".join(sorted(existing_normalized_names)) if existing_normalized_names else "(none yet)"
    return base.format(existing=existing_str)


def structure_receipt_with_llm(toon_content: str, existing_normalized_names: list[str] | None = None) -> dict:
    """
    Sends .toon content to the LLM and returns structured dict (items for the DB).
    existing_normalized_names: list of normalizedName already used by this user (evita duplicidade).
    """
    existing = existing_normalized_names or []
    preview = (toon_content[:150] + "…") if len(toon_content) > 150 else toon_content
    logger.info("LLM input: len=%d chars, preview=%s", len(toon_content), repr(preview) if preview else "(empty)")
    system_prompt = _build_system_prompt(existing)
    response = litellm.completion(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": toon_content},
        ],
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    # Validar qual modelo foi realmente usado (resposta da API)
    actual_model = getattr(response, "model", None) or getattr(response, "model_id", None)
    logger.info("LLM model: configured=%s | actual_from_api=%s", MODEL, actual_model or "unknown")
    if actual_model and actual_model != MODEL:
        # Mesmo modelo com sufixo de versão (ex: gpt-5-mini -> gpt-5-mini-2025-08-07) não é mismatch
        if actual_model.startswith(MODEL) or MODEL in actual_model:
            logger.debug("LLM using versioned model name: %s", actual_model)
        else:
            logger.warning("LLM model mismatch: requested %s but API returned %s", MODEL, actual_model)

    content = response.choices[0].message.content.strip()
    # Remove possível markdown code block
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    data = json.loads(content)
    # Garantir campos de coerência para o motor
    if "interpretation_ok" not in data:
        data["interpretation_ok"] = True
    if data.get("interpretation_ok") is False and "interpretation_message" not in data:
        data["interpretation_message"] = "Could not interpret: no reason provided"
    if "items" not in data:
        data["items"] = []
    items_count = len(data["items"])
    if data.get("interpretation_ok") is False:
        logger.info(
            "LLM returned interpretation_ok=false: message=%s, items=%d",
            data.get("interpretation_message", ""),
            items_count,
        )
    else:
        logger.info("LLM returned interpretation_ok=true: items=%d", items_count)
    return data
