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

    # 构建 302 API 请求参数（字段名对齐官方 API 文档 2026-03）
    base_url = str(request.base_url).rstrip("/")
    pay_params = {
        "app_id": PAY302_APP_ID,
        "secret": PAY302_SECRET,
        "price": amount_cents,
        "customer": {"id": client_ip, "email": ""},
        "success_url": f"{base_url}/api/payment/success",
        "back_url": base_url,
        "metadata": {"order_id": order.id, "credits": credits_to_buy},
    }

    # 生成签名并加入请求体
    pay_params["signature"] = validator.generate_signature(pay_params)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(PAY302_API_URL, json=pay_params)
            resp.raise_for_status()
            resp_json = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"支付网关错误: {e}")

    if resp_json.get("code") != 0:
        raise HTTPException(status_code=502, detail=resp_json.get("msg", "302 API 错误"))

    data = resp_json.get("data", {})
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

    302 回调 body 结构（webhook header 含 302_signature）：
    {
        "metadata": {"order_id": "...", "credits": 10},
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

    # 提取签名（body 或 header 中都可能有）
    received_signature = body.get("signature", "") or request.headers.get("302_signature", "")
    if not received_signature:
        raise HTTPException(status_code=400, detail="缺少签名")

    if not validator.validate(body, received_signature):
        raise HTTPException(status_code=401, detail="签名验证失败")

    # 提取支付信息
    payment_status_code = body.get("payment_status", 0)
    pay302_payment_order = body.get("payment_order", "")
    # 302 API 使用 metadata 字段，兼容旧版 extra
    meta = body.get("metadata") or body.get("extra") or {}
    order_id = meta.get("order_id", "") if isinstance(meta, dict) else ""

    if not order_id:
        raise HTTPException(status_code=400, detail="缺少 order_id")

    status_str = _PAY_STATUS_MAP.get(payment_status_code, "failed")

    if status_str == "paid":
        # 事务+行锁+流水幂等检查，避免并发回调重复加币
        order = await payment_crud.mark_order_paid_and_grant_credits(
            db=db,
            order_id=order_id,
            pay302_payment_order=pay302_payment_order,
            description="302 webhook 支付成功入账",
        )
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
    else:
        order = await payment_crud.mark_order_status_if_unpaid(
            db=db,
            order_id=order_id,
            status=status_str,
        )
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

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
    redirect_url = f"{base_url}/public/meetspot_finder.html?payment=success&checkout_id={checkout_id}"
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
