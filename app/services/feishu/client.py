"""飞书客户端 — 直接调用REST API，不依赖SDK链式调用"""
import logging
import time
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# token缓存
_token_cache = {"token": "", "expire_at": 0, "app_id": ""}


async def _resolve_credentials(app_id: str = "", app_secret: str = "") -> tuple[str, str]:
    """
    解析飞书凭证。优先级：
    1. 显式传入参数
    2. 数据库 lark_configs 中第一条 is_active=True 的记录
    3. 环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET
    """
    if app_id and app_secret:
        return app_id, app_secret

    # 从数据库读活跃配置
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models import LarkConfig

        async with async_session() as session:
            result = await session.execute(
                select(LarkConfig)
                .where(LarkConfig.is_active == True)
                .order_by(LarkConfig.created_at.desc())
                .limit(1)
            )
            cfg = result.scalar_one_or_none()
            if cfg and cfg.app_id and cfg.app_secret:
                return cfg.app_id, cfg.app_secret
    except Exception as e:
        logger.debug(f"DB读取飞书配置失败，回退到环境变量: {e}")

    # 回退到环境变量
    settings = get_settings()
    return settings.FEISHU_APP_ID, settings.FEISHU_APP_SECRET


async def get_tenant_access_token(app_id: str = "", app_secret: str = "") -> str:
    """
    获取tenant_access_token。
    自带缓存，过期前5分钟自动刷新。
    """
    global _token_cache

    aid, asecret = await _resolve_credentials(app_id, app_secret)

    if not aid or not asecret:
        raise ValueError("飞书App ID和App Secret未配置（请在「飞书配置」页面添加，或在 .env 中设置）")

    # 检查缓存（同一app_id且未过期）
    now = time.time()
    if (_token_cache["token"]
            and _token_cache["app_id"] == aid
            and _token_cache["expire_at"] > now + 300):
        return _token_cache["token"]

    # 请求新token
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    body = {"app_id": aid, "app_secret": asecret}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise Exception(f"获取tenant_access_token失败: code={data.get('code')}, msg={data.get('msg')}")

    token = data["tenant_access_token"]
    expire = data.get("expire", 7200)

    _token_cache = {
        "token": token,
        "expire_at": now + expire,
        "app_id": aid,
    }

    logger.info(f"飞书token已刷新，有效期{expire}秒")
    return token


async def test_connection(app_id: str = "", app_secret: str = "") -> dict:
    """测试飞书连通性"""
    try:
        token = await get_tenant_access_token(app_id, app_secret)
        return {"status": "ok", "token_prefix": token[:10] + "..."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
