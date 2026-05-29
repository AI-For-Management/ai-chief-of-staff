"""飞书客户端 — 直接调用REST API，不依赖SDK链式调用"""
import logging
import time
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# token缓存
_token_cache = {"token": "", "expire_at": 0, "app_id": ""}


async def get_tenant_access_token(app_id: str = "", app_secret: str = "") -> str:
    """
    获取tenant_access_token。
    自带缓存，过期前5分钟自动刷新。
    """
    global _token_cache

    settings = get_settings()
    aid = app_id or settings.FEISHU_APP_ID
    asecret = app_secret or settings.FEISHU_APP_SECRET

    if not aid or not asecret:
        raise ValueError("飞书App ID和App Secret未配置")

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
