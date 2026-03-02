"""FastAPI app e rota HTTPS — recebe process_id + image_b64, orquestra fluxo e atualiza status."""

import logging
import os
import threading
import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # antes de importar app.db, para DATABASE_URL vir do .env

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from app.db import (
    STATUS_ERRO,
    STATUS_PROCESSANDO,
    STATUS_PROCESSADO,
    create_receipt,
    get_existing_normalized_names,
    get_status,
    init_db,
    insert_receipt_data,
    set_status,
)
from app.llm import MODEL as LLM_MODEL, structure_receipt_with_llm
from app.ocr import run_ocr_and_save_toon
from app.storage import upload_receipt_image_b64

app = FastAPI(title="OCR Cupons Fiscais", version="1.0.0")
logger = logging.getLogger(__name__)

TOON_DIR = os.environ.get("TOON_DIR", str(Path(__file__).resolve().parent.parent / "toon_output"))
# Limite de pipelines simultâneos (evita travar com muitos usuários)
MAX_CONCURRENT_PIPELINES = int(os.environ.get("MAX_CONCURRENT_PIPELINES", "4"))
_pipeline_semaphore = threading.Semaphore(MAX_CONCURRENT_PIPELINES)


class ProcessRequest(BaseModel):
    process_id: str
    user_id: str
    image_b64: str


class ProcessResponse(BaseModel):
    process_id: str
    message: str
    status: str


class StatusResponse(BaseModel):
    process_id: str
    status: str
    error_message: str | None
    created_at: str
    updated_at: str


@app.on_event("startup")
def startup():
    init_db()
    Path(TOON_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("LLM model configured: %s (validate via GET /info or check logs after each /process)", LLM_MODEL)


def run_pipeline(process_id: str, user_id: str, image_b64: str) -> None:
    """Imagem pura → GLM-OCR (Modal) → LLM → DB. Limitado por semáforo."""
    with _pipeline_semaphore:
        _run_pipeline_impl(process_id, user_id, image_b64)


def _run_pipeline_impl(process_id: str, user_id: str, image_b64: str) -> None:
    try:
        set_status(process_id, STATUS_PROCESSANDO)
        # Upload opcional da imagem original para Cloudflare R2 (se configurado)
        r2_key = upload_receipt_image_b64(image_b64, user_id=user_id, process_id=process_id)
        if r2_key:
            logger.info("Imagem process_id=%s armazenada no R2 com key=%s", process_id, r2_key)

        ocr_text = run_ocr_and_save_toon(image_b64, process_id, TOON_DIR)
        _ocr_preview = (ocr_text[:200] + "…") if len(ocr_text) > 200 else ocr_text
        logger.info(
            "OCR result process_id=%s: len=%d chars | preview=%s",
            process_id,
            len(ocr_text),
            repr(_ocr_preview) if _ocr_preview else "(empty)",
        )
        if not ocr_text or "placeholder" in ocr_text.lower():
            logger.warning(
                "OCR returned empty or placeholder text for process_id=%s (Modal app may still use placeholder; integrate real GLM-OCR)",
                process_id,
            )

        existing_names = get_existing_normalized_names(user_id)
        logger.info("Calling LLM for process_id=%s with %d chars from OCR", process_id, len(ocr_text))
        structured = structure_receipt_with_llm(ocr_text, existing_normalized_names=existing_names)

        # Motor de coerência: se a LLM indicar que não foi possível interpretar, marcar erro e não inserir
        if structured.get("interpretation_ok") is False:
            msg = structured.get("interpretation_message") or "Could not interpret receipt."
            logger.warning(
                "Interpretation rejected process_id=%s: reason=%s | ocr_preview=%s",
                process_id,
                msg,
                repr(_ocr_preview) if _ocr_preview else "(empty)",
            )
            set_status(process_id, STATUS_ERRO, error_message=msg)
            return

        num_items = len(structured.get("items") or [])
        logger.info("Interpretation OK process_id=%s: %d items extracted", process_id, num_items)
        insert_receipt_data(
            process_id, user_id, structured,
            ocr_output=ocr_text,
            image_url=r2_key,
        )  # receipt_id = process_id
        set_status(process_id, STATUS_PROCESSADO)
        logger.info("Pipeline completed process_id=%s: status=%s", process_id, STATUS_PROCESSADO)
    except Exception as e:
        tb = traceback.format_exc()
        err_msg = f"{type(e).__name__}: {e}"
        err_detail = f"{err_msg}\n\n{tb}"
        logger.exception("Pipeline failed for process_id=%s: %s", process_id, e)
        set_status(process_id, STATUS_ERRO, error_message=err_detail)


@app.post("/process", response_model=ProcessResponse)
def process_receipt(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Recebe process_id, user_id e imagem em base64. Retorna imediatamente e processa em background.
    """
    if not request.process_id.strip():
        raise HTTPException(status_code=400, detail="process_id é obrigatório")
    if not request.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id é obrigatório")
    if not request.image_b64.strip():
        raise HTTPException(status_code=400, detail="image_b64 é obrigatório")

    create_receipt(request.process_id, request.user_id)
    set_status(request.process_id, STATUS_PROCESSANDO)
    background_tasks.add_task(run_pipeline, request.process_id, request.user_id, request.image_b64)
    return ProcessResponse(
        process_id=request.process_id,
        message="Foto recebida e encaminhada para processamento.",
        status=STATUS_PROCESSANDO,
    )


@app.get("/info")
def info():
    """Retorna configuração do serviço para validar qual modelo LLM está em uso."""
    return {
        "llm_model_configured": LLM_MODEL,
        "source": "OPENAI_MODEL env var or default gpt-5-mini",
    }


@app.get("/status/{process_id}", response_model=StatusResponse)
def status_process(process_id: str):
    """Consulta o status do processamento pelo process_id."""
    row = get_status(process_id)
    if not row:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return StatusResponse(
        process_id=row["process_id"],
        status=row["status"],
        error_message=row["error_message"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
