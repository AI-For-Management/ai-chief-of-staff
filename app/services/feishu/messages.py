"""飞书消息发送 — 文本/富文本/互动卡片"""
import json
import logging
import httpx

from app.services.feishu.client import get_tenant_access_token
from app.utils.retry import feishu_retry

logger = logging.getLogger(__name__)
BASE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"


async def _headers() -> dict:
    token = await get_tenant_access_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@feishu_retry
async def send_text(receive_id: str, text: str, receive_id_type: str = "chat_id") -> dict:
    """发送文本消息"""
    body = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            BASE_URL, headers=await _headers(),
            params={"receive_id_type": receive_id_type},
            json=body,
        )
        resp.raise_for_status()
        return resp.json().get("data", {})


@feishu_retry
async def send_interactive_card(
    receive_id: str,
    card: dict,
    receive_id_type: str = "chat_id",
) -> dict:
    """发送互动卡片消息"""
    body = {
        "receive_id": receive_id,
        "msg_type": "interactive",
        "content": json.dumps(card),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            BASE_URL, headers=await _headers(),
            params={"receive_id_type": receive_id_type},
            json=body,
        )
        resp.raise_for_status()
        return resp.json().get("data", {})


def build_approval_card(
    title: str,
    content: str,
    thread_id: str,
    actions: list[dict] | None = None,
) -> dict:
    """构建审批互动卡片"""
    if actions is None:
        actions = [
            {"tag": "button", "text": {"tag": "plain_text", "content": "✅ 确认派发"}, "type": "primary",
             "value": {"action": "approve", "thread_id": thread_id}},
            {"tag": "button", "text": {"tag": "plain_text", "content": "❌ 拒绝"}, "type": "danger",
             "value": {"action": "reject", "thread_id": thread_id}},
        ]

    return {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
        "elements": [
            {"tag": "markdown", "content": content},
            {"tag": "hr"},
            {"tag": "action", "actions": actions},
        ],
    }


def build_report_card(title: str, content: str, template: str = "blue") -> dict:
    """构建报告卡片（不含互动按钮）"""
    return {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": title}, "template": template},
        "elements": [
            {"tag": "markdown", "content": content},
        ],
    }


@feishu_retry
async def get_chat_history(chat_id: str, page_size: int = 50, start_time: str = "") -> list[dict]:
    """获取群聊历史消息"""
    url = f"https://open.feishu.cn/open-apis/im/v1/messages"
    params = {
        "container_id_type": "chat",
        "container_id": chat_id,
        "page_size": page_size,
    }
    if start_time:
        params["start_time"] = start_time

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=await _headers(), params=params)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("items", [])
