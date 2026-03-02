"""Integração com Cloudflare R2 (S3-compatível) para armazenar imagens de recibos.

- Gerar chave organizada (path) baseada em timestamp / data.
- Fazer upload da imagem (base64) para o bucket R2.
- Expiração (ex.: 30 dias) é configurada por regra no próprio bucket R2.

Configuração via .env:
- R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME
"""

from __future__ import annotations

import base64
import datetime as dt
import logging
import os
from typing import Optional

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

R2_ENDPOINT_URL = (os.environ.get("R2_ENDPOINT_URL") or "").strip() or None
R2_ACCESS_KEY_ID = (os.environ.get("R2_ACCESS_KEY_ID") or "").strip() or None
R2_SECRET_ACCESS_KEY = (os.environ.get("R2_SECRET_ACCESS_KEY") or "").strip() or None
R2_BUCKET_NAME = (os.environ.get("R2_BUCKET_NAME") or "").strip() or None


def _has_r2_config() -> bool:
    return bool(R2_ENDPOINT_URL and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME)


def _get_s3_client():
    if not _has_r2_config():
        raise RuntimeError("R2 não configurado: defina R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME no .env.")
    # Configuração básica S3-compatível para R2
    session = boto3.session.Session()
    return session.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )


def generate_receipt_key(user_id: str, process_id: str, ext: str = "jpg") -> str:
    """Gera um path organizado para o objeto no bucket.

    Estrutura: YYYY/MM/DD/YYYYMMDDTHHMMSSZ_user-process.ext
    (Sem prefixo 'receipts/' pois o bucket já se chama receipts.)
    """
    now = dt.datetime.utcnow()
    date_prefix = now.strftime("%Y/%m/%d")
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    safe_user = (user_id or "user").replace("/", "_")
    safe_proc = (process_id or "proc").replace("/", "_")
    filename = f"{ts}_{safe_user}_{safe_proc}.{ext}"
    return f"{date_prefix}/{filename}"


def upload_receipt_image_b64(image_b64: str, user_id: str, process_id: str) -> Optional[str]:
    """Faz upload da imagem (base64) para o R2.

    Retorna a chave (path) utilizada ou None se R2 não estiver configurado.
    Não lança exceção se R2 não estiver configurado; apenas loga warning.
    """
    if not _has_r2_config():
        logger.warning("R2 não configurado; pulando upload da imagem para o bucket.")
        return None

    if not image_b64:
        logger.warning("Imagem base64 vazia; não será feito upload para R2.")
        return None

    try:
        data = base64.b64decode(image_b64)
    except Exception as e:
        logger.exception("Falha ao decodificar imagem base64 para upload no R2: %s", e)
        return None

    key = generate_receipt_key(user_id=user_id, process_id=process_id, ext="jpg")
    s3 = _get_s3_client()
    try:
        s3.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType="image/jpeg",
        )
        logger.info("Imagem enviada para R2: bucket=%s key=%s size=%d bytes", R2_BUCKET_NAME, key, len(data))
        return key
    except Exception as e:
        logger.exception("Falha ao enviar imagem para R2 (bucket=%s key=%s): %s", R2_BUCKET_NAME, key, e)
        return None
