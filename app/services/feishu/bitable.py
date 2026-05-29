"""飞书多维表格(Bitable) CRUD操作"""
import logging
import httpx

from app.services.feishu.client import get_tenant_access_token
from app.utils.retry import feishu_retry

logger = logging.getLogger(__name__)
BASE_URL = "https://open.feishu.cn/open-apis/bitable/v1"


async def _headers() -> dict:
    token = await get_tenant_access_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@feishu_retry
async def list_records(
    app_token: str,
    table_id: str,
    page_size: int = 100,
    page_token: str = "",
    filter_expr: str = "",
) -> dict:
    """列出多维表格记录"""
    url = f"{BASE_URL}/apps/{app_token}/tables/{table_id}/records"
    params = {"page_size": page_size}
    if page_token:
        params["page_token"] = page_token
    if filter_expr:
        params["filter"] = filter_expr

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=await _headers(), params=params)
        resp.raise_for_status()
        return resp.json().get("data", {})


@feishu_retry
async def create_records(
    app_token: str,
    table_id: str,
    records: list[dict],
) -> dict:
    """批量创建多维表格记录"""
    url = f"{BASE_URL}/apps/{app_token}/tables/{table_id}/records/batch_create"

    body = {"records": [{"fields": r} for r in records]}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=await _headers(), json=body)
        resp.raise_for_status()
        return resp.json().get("data", {})


@feishu_retry
async def update_record(
    app_token: str,
    table_id: str,
    record_id: str,
    fields: dict,
) -> dict:
    """更新单条记录"""
    url = f"{BASE_URL}/apps/{app_token}/tables/{table_id}/records/{record_id}"

    body = {"fields": fields}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(url, headers=await _headers(), json=body)
        resp.raise_for_status()
        return resp.json().get("data", {})


@feishu_retry
async def list_fields(app_token: str, table_id: str) -> list[dict]:
    """列出多维表格字段定义"""
    url = f"{BASE_URL}/apps/{app_token}/tables/{table_id}/fields"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=await _headers())
        resp.raise_for_status()
        return resp.json().get("data", {}).get("items", [])
