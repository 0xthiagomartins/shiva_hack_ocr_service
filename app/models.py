"""SQLModel models aligned with Prisma schema (PostgreSQL). Table/column names match Prisma @@map and snake_case."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "user"
    id: str = Field(primary_key=True)
    name: str
    email: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    email_verified: bool = False
    image: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessStatus(SQLModel, table=True):
    __tablename__ = "process_status"
    process_id: str = Field(primary_key=True)
    status: str
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class Receipt(SQLModel, table=True):
    __tablename__ = "receipt"
    id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    date: datetime = Field(default_factory=datetime.utcnow)
    total_amount: float = 0.0
    currency: str = Field(default="BRL")
    image_url: Optional[str] = None
    process_id: Optional[str] = Field(default=None, foreign_key="process_status.process_id", unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Item(SQLModel, table=True):
    __tablename__ = "item"
    id: str = Field(primary_key=True)
    receipt_id: str = Field(foreign_key="receipt.id")
    raw_name: str
    normalized_name: str
    category: str
    quantity: float = 0.0
    unit_price: float = 0.0
    total_price: float = 0.0


class Session(SQLModel, table=True):
    __tablename__ = "session"
    id: str = Field(primary_key=True)
    expires_at: datetime
    token: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    user_id: str = Field(foreign_key="user.id")


class Account(SQLModel, table=True):
    __tablename__ = "account"
    id: str = Field(primary_key=True)
    account_id: str
    provider_id: str
    user_id: str = Field(foreign_key="user.id")
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    access_token_expires_at: Optional[datetime] = None
    refresh_token_expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    password: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Verification(SQLModel, table=True):
    __tablename__ = "verification"
    id: str = Field(primary_key=True)
    identifier: str
    value: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
