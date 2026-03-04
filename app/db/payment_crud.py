"""支付相关数据库操作。"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import (
    CreditBalance,
    CreditTransaction,
    FreeUsageLog,
    PaymentOrder,
)


# ============ 订单 ============


async def create_order(
    db: AsyncSession,
    user_identifier: str,
    amount_cents: int,
    credits: int,
    pay302_checkout_id: Optional[str] = None,
) -> PaymentOrder:
    """创建支付订单。"""
    order = PaymentOrder(
        user_identifier=user_identifier,
        amount_cents=amount_cents,
        credits=credits,
        pay302_checkout_id=pay302_checkout_id,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_order_by_id(db: AsyncSession, order_id: str) -> Optional[PaymentOrder]:
    """按主键 id 查询订单。"""
    stmt = select(PaymentOrder).where(PaymentOrder.id == order_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_order_status(
    db: AsyncSession,
    checkout_id: str,
    status: str,
    pay302_payment_order: Optional[str] = None,
) -> Optional[PaymentOrder]:
    """通过 checkout_id 更新订单状态。"""
    stmt = select(PaymentOrder).where(PaymentOrder.pay302_checkout_id == checkout_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        return None

    order.status = status
    if pay302_payment_order:
        order.pay302_payment_order = pay302_payment_order
    if status == "paid":
        order.paid_at = datetime.utcnow()
    await db.commit()
    await db.refresh(order)
    return order


async def get_order_by_checkout_id(
    db: AsyncSession, checkout_id: str
) -> Optional[PaymentOrder]:
    """按 checkout_id 查询订单。"""
    stmt = select(PaymentOrder).where(PaymentOrder.pay302_checkout_id == checkout_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ============ Credits 余额 ============


async def get_or_create_balance(db: AsyncSession, user_identifier: str) -> CreditBalance:
    """获取或创建用户余额记录。"""
    stmt = select(CreditBalance).where(CreditBalance.user_identifier == user_identifier)
    result = await db.execute(stmt)
    balance = result.scalar_one_or_none()
    if balance:
        return balance

    balance = CreditBalance(user_identifier=user_identifier, balance=0)
    db.add(balance)
    await db.commit()
    await db.refresh(balance)
    return balance


async def add_credits(
    db: AsyncSession,
    user_identifier: str,
    amount: int,
    order_id: Optional[str] = None,
    description: str = "充值",
) -> CreditBalance:
    """充值 credits（事务：更新余额 + 记录流水）。"""
    balance = await get_or_create_balance(db, user_identifier)
    balance.balance += amount
    balance.total_purchased += amount

    txn = CreditTransaction(
        user_identifier=user_identifier,
        amount=amount,
        order_id=order_id,
        description=description,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(balance)
    return balance


async def consume_credit(
    db: AsyncSession,
    user_identifier: str,
    amount: int = 1,
    description: str = "Agent 模式推荐",
) -> Optional[CreditBalance]:
    """消费 credits。余额不足返回 None。"""
    balance = await get_or_create_balance(db, user_identifier)
    if balance.balance < amount:
        return None

    balance.balance -= amount
    balance.total_consumed += amount

    txn = CreditTransaction(
        user_identifier=user_identifier,
        amount=-amount,
        description=description,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(balance)
    return balance


# ============ 免费次数 ============


async def get_free_usage_today(db: AsyncSession, ip_address: str) -> int:
    """查询某 IP 今日已使用的免费次数。"""
    today_start = datetime.combine(date.today(), datetime.min.time())
    stmt = (
        select(func.count())
        .select_from(FreeUsageLog)
        .where(FreeUsageLog.ip_address == ip_address)
        .where(FreeUsageLog.used_at >= today_start)
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def record_free_use(db: AsyncSession, ip_address: str) -> None:
    """记录一次免费使用。"""
    log = FreeUsageLog(ip_address=ip_address)
    db.add(log)
    await db.commit()
