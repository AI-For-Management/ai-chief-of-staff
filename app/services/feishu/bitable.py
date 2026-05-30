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


# ===========================================================
# Bitable 创建（应用层 + 表层）
# ===========================================================

DEFAULT_TASK_FIELDS = [
    {"field_name": "任务名称", "type": 1},  # 1=文本
    {"field_name": "负责人", "type": 1},
    {"field_name": "截止日期", "type": 5},  # 5=日期
    {
        "field_name": "优先级",
        "type": 3,  # 3=单选
        "property": {"options": [{"name": "high"}, {"name": "medium"}, {"name": "low"}]},
    },
    {
        "field_name": "状态",
        "type": 3,
        "property": {"options": [{"name": "待开始"}, {"name": "进行中"}, {"name": "完成"}]},
    },
]


@feishu_retry
async def create_app(name: str, folder_token: str = "") -> str:
    """
    创建一个新的多维表格应用（即一个新的 Bitable 文档）。

    Args:
        name: 多维表格名称
        folder_token: 目标文件夹token（可选，留空则在用户根目录）

    Returns:
        新建 Bitable 的 app_token
    """
    url = f"{BASE_URL}/apps"
    body = {"name": name}
    if folder_token:
        body["folder_token"] = folder_token

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=await _headers(), json=body)
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise Exception(f"create_app失败: code={data.get('code')}, msg={data.get('msg')}")

    app_info = data.get("data", {}).get("app", {})
    app_token = app_info.get("app_token", "")
    logger.info(f"创建Bitable: {name} → {app_token}")
    return app_token


@feishu_retry
async def create_table(
    app_token: str,
    table_name: str,
    fields_schema: list[dict] | None = None,
) -> str:
    """
    在指定 Bitable 中创建一张表。

    Args:
        app_token: Bitable app_token
        table_name: 新表名称
        fields_schema: 字段定义，留空则用 DEFAULT_TASK_FIELDS

    Returns:
        新表的 table_id
    """
    url = f"{BASE_URL}/apps/{app_token}/tables"
    body = {
        "table": {
            "name": table_name,
            "default_view_name": "全部",
            "fields": fields_schema or DEFAULT_TASK_FIELDS,
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=await _headers(), json=body)
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise Exception(f"create_table失败: code={data.get('code')}, msg={data.get('msg')}")

    table_id = data.get("data", {}).get("table_id", "")
    logger.info(f"创建Bitable表: {table_name} in {app_token[:12]}... → {table_id}")
    return table_id


async def create_app_with_default_table(name: str = "AI规划任务表") -> tuple[str, str]:
    """便捷封装：创建一个新Bitable + 默认任务字段表，返回 (app_token, table_id)。"""
    app_token = await create_app(name)
    table_id = await create_table(app_token, "任务", DEFAULT_TASK_FIELDS)
    return app_token, table_id
