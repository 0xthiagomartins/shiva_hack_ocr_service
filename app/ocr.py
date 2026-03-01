"""OCR via GLM-OCR hospedado na Modal.com — imagem pura, sem pré-processamento."""

import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# URL do endpoint GLM-OCR na Modal (obrigatório). Pode ser base (https://xxx.modal.run) ou já com /ocr
MODAL_OCR_URL = (os.environ.get("MODAL_OCR_URL") or "").strip().rstrip("/")
# Timeout em segundos (primeira requisição pode demorar por cold start na Modal)
MODAL_OCR_TIMEOUT = float(os.environ.get("MODAL_OCR_TIMEOUT", "120"))


def _ocr_url() -> str:
    """Modal expõe o web_endpoint na raiz da URL (ex: https://user--glm-ocr-ocr.modal.run)."""
    if not MODAL_OCR_URL:
        raise ValueError("MODAL_OCR_URL não configurado. Defina no .env o URL do endpoint GLM-OCR na Modal.")
    return MODAL_OCR_URL


def run_ocr_modal(image_b64: str) -> str:
    """
    Envia a imagem em base64 para o endpoint GLM-OCR na Modal.
    Espera POST com body {"image_b64": "..."} e resposta {"text": "..."}.
    """
    url = _ocr_url()
    logger.info(
        "Calling Modal OCR: url=%s, image_b64 len=%d chars (aguarde até ~90s na 1ª chamada, cold start)",
        url, len(image_b64 or ""),
    )
    # read timeout alto: cold start na Modal + processamento da imagem
    timeout = httpx.Timeout(MODAL_OCR_TIMEOUT)
    with httpx.Client(timeout=timeout) as client:
        r = client.post(
            url,
            json={"image_b64": image_b64},
        )
        r.raise_for_status()
        data = r.json()
    text = (data.get("text") or "").strip()
    logger.info("Modal OCR response: text len=%d chars", len(text))
    if not text and data:
        # Modal pode ter retornado text vazio com "error" no body — logar para debug
        err = data.get("error")
        if err:
            logger.warning("Modal OCR returned empty text; error from Modal: %s", err)
        else:
            logger.warning("Modal OCR returned empty text; full response keys: %s", list(data.keys()))
    return text


def save_ocr_debug(content: str, process_id: str, toon_dir: str) -> str:
    """Grava o texto OCR em {process_id}.toon para debug. Retorna o path."""
    path = Path(toon_dir)
    path.mkdir(parents=True, exist_ok=True)
    filepath = path / f"{process_id}.toon"
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


def run_ocr_and_save_toon(image_b64: str, process_id: str, toon_dir: str) -> str:
    """
    Chama GLM-OCR na Modal com a imagem pura (base64), opcionalmente salva .toon para debug.
    Retorna o texto extraído para envio à LLM.
    """
    text = run_ocr_modal(image_b64)
    save_ocr_debug(text, process_id, toon_dir)
    return text
