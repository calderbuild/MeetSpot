"""支付相关数据库操作。"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, select, text
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


async def get_order_by_id_for_update(
    db: AsyncSession, order_id: str
) -> Optional[PaymentOrder]:
    """按主键 id 查询订单并加行锁（用于并发幂等）。"""
    stmt = select(PaymentOrder).where(PaymentOrder.id == order_id).with_for_update()
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


async def mark_order_paid_and_grant_credits(
    db: AsyncSession,
    order_id: str,
    pay302_payment_order: str = "",
    description: str = "",
) -> Optional[PaymentOrder]:
    """支付成功幂等处理：订单置为 paid，并确保 credits 仅充值一次。"""
    manage_tx = not db.in_transaction()
    order = await get_order_by_id_for_update(db, order_id)
    if not order:
        return None

    if order.status != "paid":
        order.status = "paid"
        order.pay302_payment_order = pay302_payment_order
        order.paid_at = datetime.utcnow()

    # 关键幂等保障：同一 order_id 只允许出现一次充值流水
    txn_stmt = select(CreditTransaction.id).where(CreditTransaction.order_id == order.id).limit(1)
    existing_txn = await db.execute(txn_stmt)
    existing_txn_id = existing_txn.scalar_one_or_none()
    if existing_txn_id is None:
        balance = await _get_or_create_balance_no_commit(db, order.user_identifier)
        balance.balance += order.credits
        balance.total_purchased += order.credits
        db.add(
            CreditTransaction(
                user_identifier=order.user_identifier,
                amount=order.credits,
                order_id=order.id,
                description=description or f"购买 {order.credits} credits",
            )
        )

    if manage_tx:
        await db.commit()
    else:
        await db.flush()

    await db.refresh(order)
    return order


async def mark_order_status_if_unpaid(
    db: AsyncSession,
    order_id: str,
    status: str,
) -> Optional[PaymentOrder]:
    """订单失败/超时等状态更新；若已 paid 则保持不变。"""
    manage_tx = not db.in_transaction()
    order = await get_order_by_id_for_update(db, order_id)
    if not order:
        return None
    if order.status != "paid":
        order.status = status

    if manage_tx:
        await db.commit()
    else:
        await db.flush()

    await db.refresh(order)
    return order


# ============ Credits 余额 ============


async def _get_or_create_balance_no_commit(
    db: AsyncSession, user_identifier: str
) -> CreditBalance:
    """获取或创建用户余额记录（不提交事务）。"""
    stmt = select(CreditBalance).where(CreditBalance.user_identifier == user_identifier)
    result = await db.execute(stmt)
    balance = result.scalar_one_or_none()
    if balance:
        return balance

    balance = CreditBalance(user_identifier=user_identifier, balance=0)
    db.add(balance)
    await db.flush()
    return balance


async def get_or_create_balance(db: AsyncSession, user_identifier: str) -> CreditBalance:
    """获取或创建用户余额记录。"""
    balance = await _get_or_create_balance_no_commit(db, user_identifier)
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
    balance = await _get_or_create_balance_no_commit(db, user_identifier)
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
    balance = await _get_or_create_balance_no_commit(db, user_identifier)
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
    return await _get_free_usage_since(db, ip_address, today_start)


async def _get_free_usage_since(db: AsyncSession, ip_address: str, start_at: datetime) -> int:
    """查询某 IP 在指定起始时间后的使用次数（事务内复用）。"""
    stmt = (
        select(func.count())
        .select_from(FreeUsageLog)
        .where(FreeUsageLog.ip_address == ip_address)
        .where(FreeUsageLog.used_at >= start_at)
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def try_consume_free_use(
    db: AsyncSession,
    ip_address: str,
    daily_limit: int,
) -> tuple[bool, int]:
    """原子消耗一次免费额度，返回(是否成功, 当前已用次数)。"""
    if daily_limit <= 0:
        return True, 0

    manage_tx = not db.in_transaction()
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_key = date.today().isoformat()

    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        # 跨进程锁（同 IP + 当天），避免并发下超发免费额度
        lock_key = f"free_use:{ip_address}:{today_key}"
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": lock_key},
        )

    used_today = await _get_free_usage_since(db, ip_address, today_start)
    if used_today >= daily_limit:
        return False, used_today

    db.add(FreeUsageLog(ip_address=ip_address))
    if manage_tx:
        await db.commit()
    else:
        await db.flush()

    return True, used_today + 1


async def record_free_use(db: AsyncSession, ip_address: str) -> None:
    """记录一次免费使用。"""
    log = FreeUsageLog(ip_address=ip_address)
    db.add(log)
    await db.commit()
