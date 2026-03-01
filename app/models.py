"""SQLAlchemy models aligned with Prisma schema: PascalCase table names, camelCase column names."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Prisma enum ItemUnit
ItemUnitEnum = Enum("MILLILITER", "LITER", "KILOGRAM", "UNIT", "GRAM", name="ItemUnit")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "User"

    id: Mapped[str] = mapped_column("id", String, primary_key=True)
    name: Mapped[str] = mapped_column("name", String)
    email: Mapped[str] = mapped_column("email", String, unique=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=False), default=datetime.utcnow)
    emailVerified: Mapped[bool] = mapped_column("emailVerified", Boolean, default=False)
    image: Mapped[Optional[str]] = mapped_column("image", String, nullable=True)
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=False), default=datetime.utcnow)


class ProcessStatus(Base):
    __tablename__ = "ProcessStatus"

    processId: Mapped[str] = mapped_column("processId", String, primary_key=True)
    status: Mapped[str] = mapped_column("status", String)
    errorMessage: Mapped[Optional[str]] = mapped_column("errorMessage", String, nullable=True)
    createdAt: Mapped[str] = mapped_column("createdAt", String)
    updatedAt: Mapped[str] = mapped_column("updatedAt", String)


class Receipt(Base):
    __tablename__ = "Receipt"

    id: Mapped[str] = mapped_column("id", String, primary_key=True)
    userId: Mapped[str] = mapped_column("userId", String, ForeignKey("User.id"))
    date: Mapped[datetime] = mapped_column("date", DateTime(timezone=False), default=datetime.utcnow)
    totalAmount: Mapped[float] = mapped_column("totalAmount", Float, default=0.0)
    currency: Mapped[str] = mapped_column("currency", String, default="BRL")
    imageUrl: Mapped[Optional[str]] = mapped_column("imageUrl", String, nullable=True)
    processId: Mapped[Optional[str]] = mapped_column("processId", String, ForeignKey("ProcessStatus.processId"), unique=True, nullable=True)
    ocrOutput: Mapped[Optional[str]] = mapped_column("ocrOutput", Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=False), default=datetime.utcnow)


class Item(Base):
    __tablename__ = "Item"

    id: Mapped[str] = mapped_column("id", String, primary_key=True)
    receiptId: Mapped[str] = mapped_column("receiptId", String, ForeignKey("Receipt.id"))
    rawName: Mapped[str] = mapped_column("rawName", String)
    normalizedName: Mapped[str] = mapped_column("normalizedName", String)
    category: Mapped[str] = mapped_column("category", String)
    quantity: Mapped[float] = mapped_column("quantity", Float, default=0.0)
    unit: Mapped[str] = mapped_column("unit", ItemUnitEnum, nullable=False)
    unitPrice: Mapped[float] = mapped_column("unitPrice", Float, default=0.0)
    totalPrice: Mapped[float] = mapped_column("totalPrice", Float, default=0.0)


class Session(Base):
    __tablename__ = "Session"

    id: Mapped[str] = mapped_column("id", String, primary_key=True)
    expiresAt: Mapped[datetime] = mapped_column("expiresAt", DateTime(timezone=False))
    token: Mapped[str] = mapped_column("token", String, unique=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=False), default=datetime.utcnow)
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=False), default=datetime.utcnow)
    ipAddress: Mapped[Optional[str]] = mapped_column("ipAddress", String, nullable=True)
    userAgent: Mapped[Optional[str]] = mapped_column("userAgent", String, nullable=True)
    userId: Mapped[str] = mapped_column("userId", String, ForeignKey("User.id"))


class Account(Base):
    __tablename__ = "Account"

    id: Mapped[str] = mapped_column("id", String, primary_key=True)
    accountId: Mapped[str] = mapped_column("accountId", String)
    providerId: Mapped[str] = mapped_column("providerId", String)
    userId: Mapped[str] = mapped_column("userId", String, ForeignKey("User.id"))
    accessToken: Mapped[Optional[str]] = mapped_column("accessToken", String, nullable=True)
    refreshToken: Mapped[Optional[str]] = mapped_column("refreshToken", String, nullable=True)
    idToken: Mapped[Optional[str]] = mapped_column("idToken", String, nullable=True)
    accessTokenExpiresAt: Mapped[Optional[datetime]] = mapped_column("accessTokenExpiresAt", DateTime(timezone=False), nullable=True)
    refreshTokenExpiresAt: Mapped[Optional[datetime]] = mapped_column("refreshTokenExpiresAt", DateTime(timezone=False), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column("scope", String, nullable=True)
    password: Mapped[Optional[str]] = mapped_column("password", String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=False), default=datetime.utcnow)
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=False), default=datetime.utcnow)


class Verification(Base):
    __tablename__ = "Verification"

    id: Mapped[str] = mapped_column("id", String, primary_key=True)
    identifier: Mapped[str] = mapped_column("identifier", String)
    value: Mapped[str] = mapped_column("value", String)
    expiresAt: Mapped[datetime] = mapped_column("expiresAt", DateTime(timezone=False))
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=False), default=datetime.utcnow)
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=False), default=datetime.utcnow)
