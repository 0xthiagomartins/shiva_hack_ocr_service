"""DB layer — SQLAlchemy, aligned with Prisma (User, Receipt, Item, ProcessStatus)."""

import os
import uuid
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Base, Item, ProcessStatus, Receipt, User

# Path padrão para SQLite; ignorado quando DATABASE_URL é PostgreSQL
_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "receipts.db"

DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{_DEFAULT_PATH}"
_IS_SQLITE = "sqlite" in DATABASE_URL
_IS_MEMORY = ":memory:" in (DATABASE_URL or "")

# Para SQLite :memory: usar StaticPool para todas as conexões verem o mesmo DB (evita "no such table" nos testes)
if _IS_MEMORY:
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if _IS_SQLITE else {},
        pool_pre_ping=True,
    )

# Pipeline status constants
STATUS_PROCESSANDO = "em processamento"
STATUS_PROCESSADO = "processado"
STATUS_ERRO = "erro"


def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"


def init_db():
    """Create all tables. For SQLite (non-memory) only: ensure data dir exists."""
    if _IS_SQLITE and not _IS_MEMORY:
        Path(_DEFAULT_PATH).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def set_status(process_id: str, status: str, error_message: str | None = None):
    now = _now()
    with Session(engine) as session:
        existing = session.get(ProcessStatus, process_id)
        if existing:
            existing.status = status
            existing.errorMessage = error_message
            existing.updatedAt = now
            session.add(existing)
        else:
            session.add(ProcessStatus(processId=process_id, status=status, errorMessage=error_message, createdAt=now, updatedAt=now))
        session.commit()


def get_status(process_id: str) -> dict | None:
    with Session(engine) as session:
        row = session.get(ProcessStatus, process_id)
    if not row:
        return None
    return {
        "process_id": row.processId,
        "status": row.status,
        "error_message": row.errorMessage,
        "created_at": row.createdAt,
        "updated_at": row.updatedAt,
    }


def create_receipt(receipt_id: str, user_id: str):
    """Create Receipt at start of processing (id = process_id). Idempotent: skip if Receipt already exists."""
    from datetime import datetime
    with Session(engine) as session:
        if session.get(Receipt, receipt_id) is not None:
            return
        session.add(Receipt(
            id=receipt_id,
            userId=user_id,
            processId=receipt_id,
            date=datetime.utcnow(),
            totalAmount=0.0,
            currency="BRL",
        ))
        session.commit()


def insert_receipt_data(receipt_id: str, user_id: str, structured: dict):
    """
    Create Items from LLM output and update Receipt.totalAmount.
    structured: {"items": [{"description", "normalized_name", "quantity", "unit_price", "total_value"}, ...]}
    description -> rawName; normalized_name -> normalizedName (generic: "Aveia", "Leite", etc.).
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
            normalized = (row.get("normalized_name") or "").strip() or raw
            total_amount += tv
            session.add(Item(
                id=str(uuid.uuid4()),
                receiptId=receipt_id,
                rawName=raw,
                normalizedName=normalized,
                category="Uncategorized",
                quantity=qty,
                unitPrice=up,
                totalPrice=tv,
            ))
        receipt = session.get(Receipt, receipt_id)
        if receipt:
            receipt.totalAmount = total_amount
            session.add(receipt)
        session.commit()


def count_items_by_receipt(receipt_id: str) -> int:
    """Returns the number of Item rows for the given receipt_id."""
    with Session(engine) as session:
        result = session.execute(select(Item).where(Item.receiptId == receipt_id))
        return len(result.scalars().all())


def get_receipt_total(receipt_id: str) -> float | None:
    """Returns Receipt.totalAmount for the given id, or None."""
    with Session(engine) as session:
        r = session.get(Receipt, receipt_id)
        return float(r.totalAmount) if r else None
