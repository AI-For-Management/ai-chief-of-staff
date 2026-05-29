"""飞书Webhook接收端点 — 事件订阅 + 卡片回调"""
import json
import logging

from fastapi import APIRouter, Request

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/feishu")
async def feishu_webhook(request: Request):
    """
    飞书事件回调统一入口
    处理: 1.URL验证挑战 2.事件订阅 3.卡片按钮回调
    """
    body = await request.json()
    settings = get_settings()

    # 1. URL验证挑战 (首次配置webhook时飞书会发送)
    if body.get("type") == "url_verification":
        challenge = body.get("challenge", "")
        logger.info(f"飞书URL验证: challenge={challenge}")
        return {"challenge": challenge}

    # 2. 验证token
    header = body.get("header", {})
    token = header.get("token", "") or body.get("token", "")
    if settings.FEISHU_VERIFICATION_TOKEN and token != settings.FEISHU_VERIFICATION_TOKEN:
        logger.warning(f"飞书Webhook token验证失败: {token}")
        return {"code": 1, "msg": "token mismatch"}

    event_type = header.get("event_type", "")

    # 3. 卡片按钮回调
    if event_type == "card.action.trigger" or body.get("action"):
        return await _handle_card_action(body)

    # 4. 消息事件
    if event_type == "im.message.receive_v1":
        return await _handle_message_event(body)

    logger.info(f"收到飞书事件: {event_type}")
    return {"code": 0, "msg": "ok"}


async def _handle_card_action(body: dict) -> dict:
    """处理互动卡片按钮点击"""
    action = body.get("event", {}).get("action", body.get("action", {}))
    value = action.get("value", {})

    thread_id = value.get("thread_id", "")
    action_type = value.get("action", "")

    logger.info(f"卡片回调: thread_id={thread_id}, action={action_type}")

    if thread_id and action_type in ("approve", "reject"):
        try:
            from app.agents.task_graph import resume_task_dispatch
            approved = action_type == "approve"
            await resume_task_dispatch(thread_id, approved)
            logger.info(f"HITL恢复成功: thread_id={thread_id}, approved={approved}")
        except Exception as e:
            logger.error(f"HITL恢复失败: {e}")

    return {"code": 0, "msg": "ok"}


async def _handle_message_event(body: dict) -> dict:
    """处理收到的消息事件"""
    event = body.get("event", {})
    message = event.get("message", {})
    msg_type = message.get("message_type", "")
    chat_id = message.get("chat_id", "")

    if msg_type == "text":
        content = json.loads(message.get("content", "{}"))
        text = content.get("text", "")
        logger.info(f"收到消息: chat_id={chat_id}, text={text[:50]}")
        # Phase 3+ 实现时这里会路由到Agent处理

    return {"code": 0, "msg": "ok"}
