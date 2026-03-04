"""支付相关 API 路由。

基于 302.AI Pay with 302 官方 API 文档和 demo 实现。
API 文档: https://302ai.apifox.cn/376945253e0
"""

import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import payment_crud
from app.db.database import get_db
from app.models.payment import (
    BalanceResponse,
    CreateOrderRequest,
    FreeRemainingResponse,
    OrderStatusResponse,
)
from app.payment.signature import SignatureValidator

router = APIRouter(prefix="/api/payment", tags=["payment"])

# 环境变量
PAY302_APP_ID = os.getenv("PAY302_APP_ID", "ccff86524c")
PAY302_SECRET = os.getenv("PAY302_SECRET", "")
PAY302_API_URL = os.getenv("PAY302_API_URL", "https://api.302.ai/v1/checkout")
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "1"))
CREDIT_PRICE_CENTS = int(os.getenv("CREDIT_PRICE_CENTS", "100"))
CREDITS_PER_PURCHASE = int(os.getenv("CREDITS_PER_PURCHASE", "10"))

# 302 Webhook payment_status 枚举
_PAY_STATUS_MAP = {
    0: "pending",    # 未支付
    1: "paid",       # 支付完成
    -1: "failed",    # 失败
    -2: "timeout",   # 超时
}


def _get_client_ip(request: Request) -> str:
    """获取客户端 IP，优先读取代理头。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_validator() -> SignatureValidator:
    """获取签名验证器。未配置 secret 时抛出异常。"""
    if not PAY302_SECRET:
        raise HTTPException(status_code=503, detail="支付服务未配置")
    return SignatureValidator(PAY302_SECRET)


# ============ 创建订单 ============


@router.post("/create")
async def create_order(
    payload: CreateOrderRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """创建支付订单并调用 302 API 获取 checkout_url。

    流程：
    1. 本地创建订单记录
    2. 构建 302 API 参数（含 secret + signature）
    3. POST /v1/checkout 获取 checkout_url
    4. 前端跳转 checkout_url 完成支付
    """
    validator = _get_validator()
    client_ip = _get_client_ip(request)

    credits_to_buy = payload.credits or CREDITS_PER_PURCHASE
    # amount 单位为美分
    amount_cents = (credits_to_buy * CREDIT_PRICE_CENTS) // CREDITS_PER_PURCHASE

    # 本地创建订单
    order = await payment_crud.create_order(
        db,
        user_identifier=client_ip,
        amount_cents=amount_cents,
        credits=credits_to_buy,
    )

    # 构建 302 API 请求参数（参考 demo create/route.ts）
    base_url = str(request.base_url).rstrip("/")
    pay_params = {
        "app_id": PAY302_APP_ID,
        "secret": PAY302_SECRET,
        "amount": amount_cents,
        "user_name": client_ip,
        "email": "",
        "suc_url": f"{base_url}/api/payment/success",
        "back_url": base_url,
        "fail_url": base_url,
        "extra": {"order_id": order.id, "credits": credits_to_buy},
    }

    # 生成签名并加入请求体
    pay_params["signature"] = validator.generate_signature(pay_params)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(PAY302_API_URL, json=pay_params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"支付网关错误: {e}")

    # 302 API 返回 id 即为 checkout_id
    checkout_id = data.get("id", "")
    checkout_url = data.get("checkout_url", "")

    # 回写 checkout_id
    if checkout_id:
        order.pay302_checkout_id = checkout_id
        await db.commit()

    return {
        "success": True,
        "order_id": order.id,
        "checkout_id": checkout_id,
        "checkout_url": checkout_url,
        "credits": credits_to_buy,
        "amount_cents": amount_cents,
    }


# ============ Webhook 回调 ============


@router.post("/webhook")
async def payment_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """接收 302 支付回调，验签后更新订单并充值 credits。

    302 回调 body 结构：
    {
        "extra": {"order_id": "...", "credits": 10},
        "payment_order": "302平台订单号",
        "payment_fee": 0,
        "payment_amount": 100,
        "payment_status": 1,  // 0=未支付, 1=成功, -1=失败, -2=超时
        "app_id": "ccff86524c",
        "signature": "HMAC-SHA256签名"
    }
    """
    validator = _get_validator()

    body = await request.json()

    # 验证 app_id
    if body.get("app_id") != PAY302_APP_ID:
        raise HTTPException(status_code=403, detail="app_id 不匹配")

    # 提取签名（signature 字段在验签时会被自动排除）
    received_signature = body.get("signature", "")
    if not received_signature:
        raise HTTPException(status_code=400, detail="缺少签名")

    if not validator.validate(body, received_signature):
        raise HTTPException(status_code=401, detail="签名验证失败")

    # 提取支付信息
    payment_status_code = body.get("payment_status", 0)
    pay302_payment_order = body.get("payment_order", "")
    extra = body.get("extra", {})
    order_id = extra.get("order_id", "") if isinstance(extra, dict) else ""

    if not order_id:
        raise HTTPException(status_code=400, detail="缺少 order_id")

    # 通过 order_id 查找本地订单
    order = await payment_crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 幂等：已处理过的订单直接返回成功
    if order.status == "paid":
        return {"success": True, "message": "已处理"}

    status_str = _PAY_STATUS_MAP.get(payment_status_code, "failed")

    if status_str == "paid":
        order.status = "paid"
        order.pay302_payment_order = pay302_payment_order
        from datetime import datetime
        order.paid_at = datetime.utcnow()
        await db.commit()

        await payment_crud.add_credits(
            db,
            user_identifier=order.user_identifier,
            amount=order.credits,
            order_id=order.id,
            description=f"购买 {order.credits} credits",
        )
    else:
        order.status = status_str
        await db.commit()

    # 必须返回 200 OK 告诉 302 平台已收到
    return {"success": True}


# ============ 支付成功回跳 ============


@router.get("/success")
async def payment_success(request: Request):
    """支付成功后的前端回跳页面。

    302 会在 query 参数中带上 checkout_id 和 302_signature。
    此端点重定向回首页，前端可根据 checkout_id 轮询订单状态。
    """
    from fastapi.responses import RedirectResponse

    checkout_id = request.query_params.get("checkout_id", "")
    base_url = str(request.base_url).rstrip("/")
    redirect_url = f"{base_url}/?payment=success&checkout_id={checkout_id}"
    return RedirectResponse(url=redirect_url)


# ============ 查询接口 ============


@router.get("/status/{checkout_id}", response_model=OrderStatusResponse)
async def get_order_status(
    checkout_id: str, db: AsyncSession = Depends(get_db)
):
    """查询订单状态（按本地 checkout_id）。"""
    order = await payment_crud.get_order_by_checkout_id(db, checkout_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return OrderStatusResponse(
        order_id=order.id,
        status=order.status,
        credits=order.credits,
        amount_cents=order.amount_cents,
        created_at=order.created_at,
        paid_at=order.paid_at,
    )


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(request: Request, db: AsyncSession = Depends(get_db)):
    """查询当前用户 credits 余额（按 IP 识别）。"""
    client_ip = _get_client_ip(request)
    bal = await payment_crud.get_or_create_balance(db, client_ip)
    return BalanceResponse(
        user_identifier=client_ip,
        balance=bal.balance,
        total_purchased=bal.total_purchased,
        total_consumed=bal.total_consumed,
    )


@router.get("/free-remaining", response_model=FreeRemainingResponse)
async def get_free_remaining(request: Request, db: AsyncSession = Depends(get_db)):
    """查询今日剩余免费次数。"""
    client_ip = _get_client_ip(request)
    used = await payment_crud.get_free_usage_today(db, client_ip)
    remaining = max(0, FREE_DAILY_LIMIT - used)
    return FreeRemainingResponse(
        remaining=remaining,
        daily_limit=FREE_DAILY_LIMIT,
        used_today=used,
    )
