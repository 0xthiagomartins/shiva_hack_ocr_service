"""LiteLLM + OpenAI (modelo mini); estruturação do texto no modelo do banco."""

import json
import os

import litellm


# Modelo mini para baixo custo
MODEL = "gpt-4o-mini"


SYSTEM_PROMPT = """You extract receipt items from OCR text. The text may come from up to 4 OCR variants (may have misreads). Analyze all and output a single consolidated list of items.

Reply ONLY with valid JSON, no markdown or extra text, in this format:
{"items": [{"description": "product name", "quantity": number, "unit": "UN or KG or L etc", "unit_price": number with 2 decimals, "total_value": number with 2 decimals}]}

- description: product/item name
- quantity: number (integer or decimal)
- unit: UN, KG, L, CX, etc.
- unit_price and total_value: numbers with 2 decimal places
If a field cannot be extracted, use null. Include every item you identify on the receipt."""


def structure_receipt_with_llm(toon_content: str) -> dict:
    """
    Sends .toon content to the LLM and returns structured dict (items for the DB).
    """
    response = litellm.completion(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
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
