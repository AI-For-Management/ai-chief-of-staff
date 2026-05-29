"""飞书任务API v2 — 创建和指派任务"""
import json
import logging
import httpx

from app.services.feishu.client import get_tenant_access_token
from app.utils.retry import feishu_retry

logger = logging.getLogger(__name__)
BASE_URL = "https://open.feishu.cn/open-apis/task/v2/tasks"


async def _headers() -> dict:
    token = await get_tenant_access_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@feishu_retry
async def create_task(
    summary: str,
    description: str = "",
    due_timestamp: str = "",
    assignee_ids: list[str] | None = None,
) -> dict:
    """
    创建飞书任务

    Args:
        summary: 任务标题
        description: 任务描述
        due_timestamp: 截止时间戳(秒)
        assignee_ids: 负责人open_id列表
    """
    body = {
        "summary": summary,
        "description": description,
    }

    if due_timestamp:
        body["due"] = {"timestamp": due_timestamp, "is_all_day": False}

    if assignee_ids:
        body["members"] = [
            {"id": uid, "type": "user", "role": "assignee"}
            for uid in assignee_ids
        ]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(BASE_URL, headers=await _headers(), json=body)
        resp.raise_for_status()
        return resp.json().get("data", {})


@feishu_retry
async def list_tasks(page_size: int = 50) -> list[dict]:
    """列出任务"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            BASE_URL, headers=await _headers(),
            params={"page_size": page_size},
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("items", [])
