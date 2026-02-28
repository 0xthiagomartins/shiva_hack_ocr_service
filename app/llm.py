"""LiteLLM + OpenAI (modelo mini); estruturação do texto no modelo do banco."""

import json
import os

import litellm


MODEL = "gpt-4o-mini"


def _build_system_prompt(existing_normalized_names: list[str]) -> str:
    base = """You extract receipt items from OCR text. The text may come from up to 8 OCR variants (different brightness/contrast, may have misreads). Analyze all and output a single consolidated list of items.

CRITICAL: List ONLY items that appear in the OCR text. Do NOT invent, assume or add products that are not clearly present in the text. If the text is empty or unreadable, return {{"items": []}}.

AVOID DUPLICATE NORMALIZED NAMES: This user already has the following normalized_name values in their history. You MUST prefer reusing one of these when the product is the same or very similar (e.g. if "Coca-Cola" exists, use "Coca-Cola" for Coke products, not "Coca"). Only create a new normalized_name when no existing one fits. This keeps categories consistent and avoids duplicates like "Coca" and "Coca-Cola".
Existing normalized names for this user: {existing}

Reply ONLY with valid JSON, no markdown or extra text, in this format:
{{"items": [{{"description": "product name as on receipt", "normalized_name": "generic product name", "quantity": number, "unit": "UNIT|LITER|MILLILITER|KILOGRAM|GRAM", "unit_price": number with 2 decimals, "total_value": number with 2 decimals}}]}}

- description: product name exactly as read on the receipt (e.g. "AVEIA NESTLE FLOCOS 170G", "LEITE L VIDA ITALAC 1L")
- normalized_name: generic product name. PREFER reusing one from the existing list above when it matches. Otherwise one or two words, capitalized, no brand/size (e.g. "Aveia", "Leite").
- quantity: number (integer or decimal)
- unit: MUST be exactly one of: UNIT (unidade/cx/embalagem), LITER (L), MILLILITER (ml), KILOGRAM (kg), GRAM (g).
- unit_price and total_value: numbers with 2 decimal places
If a field cannot be extracted, use null. Include every item you identify on the receipt, and no others."""
    existing_str = ", ".join(sorted(existing_normalized_names)) if existing_normalized_names else "(none yet)"
    return base.format(existing=existing_str)


def structure_receipt_with_llm(toon_content: str, existing_normalized_names: list[str] | None = None) -> dict:
    """
    Sends .toon content to the LLM and returns structured dict (items for the DB).
    existing_normalized_names: list of normalizedName already used by this user (evita duplicidade).
    """
    existing = existing_normalized_names or []
    system_prompt = _build_system_prompt(existing)
    response = litellm.completion(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": toon_content},
        ],
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    content = response.choices[0].message.content.strip()
    # Remove possível markdown code block
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    return json.loads(content)
