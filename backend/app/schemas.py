from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

# Timestamps are stored as naive UTC; always serialise with a Z suffix.
UTCDateTime = Annotated[
    datetime,
    PlainSerializer(lambda d: d.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                    return_type=str, when_used="json")]
Money = Annotated[Decimal, PlainSerializer(lambda d: f"{d:.2f}", return_type=str, when_used="json")]

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    woo_customer_id: Optional[int]
    name: str
    email: Optional[str]
    phone: Optional[str]
    is_guest: bool
    total_orders: int = 0
    total_spent: Money = Decimal("0")
    currency: Optional[str] = None
    last_order_date: Optional[UTCDateTime] = None


class CustomerDetail(CustomerOut):
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
    created_at: UTCDateTime


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    woo_product_id: Optional[int]
    name: str
    quantity: int
    unit_price: Money


class OrderOut(BaseModel):
    id: int
    source: str
    woo_order_id: int
    order_number: str
    status: str
    total: Money
    currency: str
    order_date: Optional[UTCDateTime]
    customer_id: Optional[int]
    customer_name: Optional[str]
    billing_email: Optional[str]
    is_guest: bool
    item_count: int = 0
    last_synced_at: UTCDateTime


class OrderDetail(OrderOut):
    items: List[OrderItemOut]


class InteractionCreate(BaseModel):
    type: Literal["note", "call", "email", "meeting"] = "note"
    summary: str = Field(min_length=1, max_length=2000)

    @field_validator("summary")
    @classmethod
    def _strip(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Note cannot be empty")
        return v


class InteractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    type: str
    summary: str
    created_at: UTCDateTime


class FollowUpCreate(BaseModel):
    customer_id: int
    title: str = Field(min_length=1, max_length=200)
    due_date: date

    @field_validator("title")
    @classmethod
    def _strip(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v


class FollowUpUpdate(BaseModel):
    status: Literal["pending", "completed"]


class FollowUpOut(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    order_id: Optional[int]
    order_number: Optional[str]
    title: str
    due_date: date
    status: str
    automatic: bool
    created_at: UTCDateTime
    completed_at: Optional[UTCDateTime]


class ModeUpdate(BaseModel):
    mode: Literal["real", "demo"]


class MessageTemplateOut(BaseModel):
    subject: str
    body: str
    note: str = "Review and send from your own email client. The CRM does not send email."
