from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

SOURCE_REAL = "woocommerce"
SOURCE_DEMO = "demo"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("source", "woo_customer_id", name="uq_customer_source_woo"),
        UniqueConstraint("source", "email", name="uq_customer_source_email"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default=SOURCE_REAL, index=True)
    woo_customer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    address_line: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    postcode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    orders = relationship("Order", back_populates="customer")
    interactions = relationship("Interaction", back_populates="customer", cascade="all, delete-orphan")
    tasks = relationship("FollowUpTask", back_populates="customer", cascade="all, delete-orphan")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("source", "woo_order_id", name="uq_order_source_woo"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_date", "order_date"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default=SOURCE_REAL, index=True)
    woo_order_id: Mapped[int] = mapped_column(Integer)
    customer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    order_number: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))  # exactly as reported by WooCommerce
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), default="")
    order_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Order-level contact snapshot (used for guest orders with no CRM customer link).
    billing_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    woo_product_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    order = relationship("Order", back_populates="items")


class Interaction(Base):
    __tablename__ = "interactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20), default="note")  # note|call|email|meeting|system
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    customer = relationship("Customer", back_populates="interactions")


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Idempotency key for automatically created tasks; NULL for manual tasks.
    external_event_id: Mapped[Optional[str]] = mapped_column(String(190), nullable=True, unique=True)
    customer = relationship("Customer", back_populates="tasks")
    order = relationship("Order")


class SyncLog(Base):
    __tablename__ = "sync_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default=SOURCE_REAL, index=True)
    entity_type: Mapped[str] = mapped_column(String(30))  # sync|customer|order|webhook
    external_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True)  # success|error|skipped
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 of raw body
    delivery_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="received")  # received|processed|error
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
