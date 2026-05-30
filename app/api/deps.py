"""FastAPI 依赖注入 — 鉴权、租户等"""
from fastapi import HTTPException, Header, status
from app.config import get_settings


async def require_admin_token(authorization: str = Header(default="")) -> None:
    """
    /api/admin/* 端点的 Bearer 鉴权依赖。

    如果配置了 ADMIN_API_TOKEN：
    - 请求头必须 Authorization: Bearer <token>
    - 不匹配返回 401
    如果未配置：开发模式，跳过鉴权（仅本地）
    """
    settings = get_settings()
    expected = (settings.ADMIN_API_TOKEN or "").strip()

    # 开发模式：未配置 token 时跳过（生产强制配置）
    if not expected:
        if (settings.APP_ENV or "").lower() == "production":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="生产模式下必须配置 ADMIN_API_TOKEN",
            )
        return

    auth = (authorization or "").strip()
    if not auth.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 Authorization: Bearer <token> 头",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth[7:].strip()
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )
