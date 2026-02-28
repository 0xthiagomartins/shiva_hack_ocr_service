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
from app.llm import structure_receipt_with_llm
from app.ocr import run_ocr_and_save_toon
from app.preprocess import get_eight_variations

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


def run_pipeline(process_id: str, user_id: str, image_b64: str) -> None:
    """Preprocess, OCR, LLM, then insert Items and update Receipt.total_amount. Limitado por semáforo."""
    with _pipeline_semaphore:
        _run_pipeline_impl(process_id, user_id, image_b64)


def _run_pipeline_impl(process_id: str, user_id: str, image_b64: str) -> None:
    try:
        set_status(process_id, STATUS_PROCESSANDO)
        images = get_eight_variations(image_b64)
        toon_content = run_ocr_and_save_toon(images, process_id, TOON_DIR)

        existing_names = get_existing_normalized_names(user_id)
        structured = structure_receipt_with_llm(toon_content, existing_normalized_names=existing_names)

        # Motor de coerência: se a LLM indicar que não foi possível interpretar, marcar erro e não inserir
        if structured.get("interpretation_ok") is False:
            msg = structured.get("interpretation_message") or "Could not interpret receipt."
            logger.warning("Interpretation rejected for process_id=%s: %s", process_id, msg)
            set_status(process_id, STATUS_ERRO, error_message=msg)
            return

        insert_receipt_data(process_id, user_id, structured)  # receipt_id = process_id
        set_status(process_id, STATUS_PROCESSADO)
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
