"""DB layer — SQLModel, aligned with Prisma (User, Receipt, Item). ProcessStatus for pipeline."""

import os
import uuid
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.models import Item, ProcessStatus, Receipt, User

# Path padrão para SQLite; ignorado quando DATABASE_URL é PostgreSQL
_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "receipts.db"

DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{_DEFAULT_PATH}"
_IS_SQLITE = "sqlite" in DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _IS_SQLITE else {},
    pool_pre_ping=True,  # detecta conexões mortas (útil para Postgres)
)

# Pipeline status constants
STATUS_PROCESSANDO = "em processamento"
STATUS_PROCESSADO = "processado"
STATUS_ERRO = "erro"


def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"


def init_db():
    """Create all tables. For SQLite only: ensure data dir exists."""
    if _IS_SQLITE:
        Path(_DEFAULT_PATH).parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def set_status(process_id: str, status: str, error_message: str | None = None):
    now = _now()
    with Session(engine) as session:
        existing = session.get(ProcessStatus, process_id)
        if existing:
            existing.status = status
            existing.error_message = error_message
            existing.updated_at = now
            session.add(existing)
        else:
            session.add(ProcessStatus(process_id=process_id, status=status, error_message=error_message, created_at=now, updated_at=now))
        session.commit()


def get_status(process_id: str) -> dict | None:
    with Session(engine) as session:
        row = session.get(ProcessStatus, process_id)
    if not row:
        return None
    return {
        "process_id": row.process_id,
        "status": row.status,
        "error_message": row.error_message,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def create_receipt(receipt_id: str, user_id: str):
    """Create Receipt at start of processing (id = process_id). Links to ProcessStatus via process_id. User must exist."""
    from datetime import datetime
    with Session(engine) as session:
        session.add(Receipt(
            id=receipt_id,
            user_id=user_id,
            process_id=receipt_id,
            date=datetime.utcnow(),
            total_amount=0.0,
            currency="BRL",
        ))
        session.commit()


def insert_receipt_data(receipt_id: str, user_id: str, structured: dict):
    """
    Create Items from LLM output and update Receipt.total_amount.
    structured: {"items": [{"description", "quantity", "unit_price", "total_value"}, ...]}
    Maps description -> raw_name; normalized_name/category set for later AI step.
    """
    from datetime import datetime
    items_data = structured.get("items") or []
    total_amount = 0.0
    with Session(engine) as session:
        for row in items_data:
            qty = float(row.get("quantity") or 0)
            up = float(row.get("unit_price") or 0)
            tv = float(row.get("total_value") or (qty * up))
            raw = (row.get("description") or "").strip() or "—"
            total_amount += tv
            session.add(Item(
                id=str(uuid.uuid4()),
                receipt_id=receipt_id,
                raw_name=raw,
                normalized_name=raw,  # categorizer service fills later
                category="Uncategorized",  # categorizer service fills later
                quantity=qty,
                unit_price=up,
                total_price=tv,
            ))
        receipt = session.get(Receipt, receipt_id)
        if receipt:
            receipt.total_amount = total_amount
            session.add(receipt)
        session.commit()


def count_items_by_receipt(receipt_id: str) -> int:
    """Returns the number of Item rows for the given receipt_id."""
    with Session(engine) as session:
        from sqlmodel import select
        return len(session.exec(select(Item).where(Item.receipt_id == receipt_id)).all())


def get_receipt_total(receipt_id: str) -> float | None:
    """Returns Receipt.total_amount for the given id, or None."""
    with Session(engine) as session:
        r = session.get(Receipt, receipt_id)
        return float(r.total_amount) if r else None
