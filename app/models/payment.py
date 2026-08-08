"""支付相关 SQLAlchemy 模型与 Pydantic 模式。"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.db.database import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


# ============ SQLAlchemy 模型 ============


class PaymentOrder(Base):
    """支付订单。"""

    __tablename__ = "payment_orders"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    user_identifier = Column(String(128), nullable=False, index=True)  # IP 或 user_id
    amount_cents = Column(Integer, nullable=False)  # 金额（分）
    credits = Column(Integer, nullable=False)  # 购买的 credits 数
    status = Column(String(20), nullable=False, default="pending")  # pending/paid/failed/timeout
    pay302_checkout_id = Column(String(128), unique=True, nullable=True, index=True)
    pay302_payment_order = Column(String(128), nullable=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)


class CreditBalance(Base):
    """用户 Credits 余额。"""

    __tablename__ = "credit_balances"

    user_identifier = Column(String(128), primary_key=True)
    balance = Column(Integer, nullable=False, default=0)
    total_purchased = Column(Integer, nullable=False, default=0)
    total_consumed = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CreditTransaction(Base):
    """Credits 流水记录。"""

    __tablename__ = "credit_transactions"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    user_identifier = Column(String(128), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # 正数=充值，负数=消费
    order_id = Column(String(36), nullable=True)  # 关联订单（充值时非空）
    description = Column(String(255), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FreeUsageLog(Base):
    """每日免费使用记录。"""

    __tablename__ = "free_usage_logs"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    ip_address = Column(String(45), nullable=False, index=True)  # IPv4/IPv6
    used_at = Column(DateTime(timezone=True), server_default=func.now())


# ============ Pydantic 模式 ============


class CreateOrderRequest(BaseModel):
    credits: int = Field(default=10, ge=1, description="购买的 credits 数量")


class OrderStatusResponse(BaseModel):
    order_id: str
    status: str
    credits: int
    amount_cents: int
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    user_identifier: str
    balance: int
    total_purchased: int
    total_consumed: int


class FreeRemainingResponse(BaseModel):
    remaining: int
    daily_limit: int
    used_today: int
