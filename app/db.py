"""DB layer — SQLAlchemy, aligned with Prisma. Suporta PostgreSQL (DATABASE_URL no .env) ou SQLite."""

import os
import uuid
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Base, Item, ProcessStatus, Receipt, User

# DATABASE_URL no .env: use postgresql://... para Postgres; fallback SQLite local
_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "receipts.db"
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{_DEFAULT_PATH}"
_IS_SQLITE = "sqlite" in (DATABASE_URL or "")
_IS_MEMORY = ":memory:" in (DATABASE_URL or "")

# SQLite :memory: (testes) → StaticPool; Postgres/SQLite arquivo → pool normal
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

STATUS_PROCESSANDO = "Processing"
STATUS_PROCESSADO = "Processed"
STATUS_ERRO = "Error"


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


def ensure_user_exists(user_id: str) -> None:
    """Cria o User na tabela User (por id) se não existir, para satisfazer FK Receipt.userId -> User.id."""
    from datetime import datetime
    with Session(engine) as session:
        if session.get(User, user_id) is not None:
            return
        session.add(User(
            id=user_id,
            name="User",
            email=f"{user_id}@ocr.local",
        ))
        session.commit()


def create_receipt(receipt_id: str, user_id: str):
    """Create Receipt at start of processing (id = process_id). Idempotent: skip if Receipt already exists."""
    from datetime import datetime
    ensure_user_exists(user_id)
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


VALID_ITEM_UNITS = {"MILLILITER", "LITER", "KILOGRAM", "UNIT", "GRAM"}


def _normalize_unit(value: str) -> str:
    """Mapeia valor do LLM para enum ItemUnit; default UNIT."""
    if not value:
        return "UNIT"
    u = str(value).strip().upper()
    if u in VALID_ITEM_UNITS:
        return u
    if u in ("ML", "MILILITRO", "MILILITROS"):
        return "MILLILITER"
    if u in ("L", "LITRO", "LITROS"):
        return "LITER"
    if u in ("KG", "QUILO", "QUILOS"):
        return "KILOGRAM"
    if u in ("G", "GRAMA", "GRAMAS"):
        return "GRAM"
    return "UNIT"


def insert_receipt_data(receipt_id: str, user_id: str, structured: dict):
    """
    Create Items from LLM output and update Receipt.totalAmount.
    structured: {"items": [{"description", "normalized_name", "quantity", "unit", "unit_price", "total_value"}, ...]}
    unit: ItemUnit enum (UNIT, LITER, MILLILITER, KILOGRAM, GRAM).
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
            unit = _normalize_unit(row.get("unit") or "")
            total_amount += tv
            session.add(Item(
                id=str(uuid.uuid4()),
                receiptId=receipt_id,
                rawName=raw,
                normalizedName=normalized,
                category="Uncategorized",
                quantity=qty,
                unit=unit,
                unitPrice=up,
                totalPrice=tv,
            ))
        receipt = session.get(Receipt, receipt_id)
        if receipt:
            receipt.totalAmount = total_amount
            session.add(receipt)
        session.commit()


def get_existing_normalized_names(user_id: str) -> list[str]:
    """Lista todos os normalizedName distintos dos itens dos recibos desse user_id (evitar duplicidade)."""
    with Session(engine) as session:
        result = session.execute(
            select(Item.normalizedName).join(Receipt, Item.receiptId == Receipt.id).where(Receipt.userId == user_id).distinct()
        )
        return [row[0] for row in result.all() if row[0]]


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
