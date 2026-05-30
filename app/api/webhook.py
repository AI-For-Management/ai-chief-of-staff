"""飞书Webhook接收端点 — 事件订阅 + 卡片回调"""
import json
import logging

from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

# 防御飞书事件风暴：单 IP 每分钟最多 120 次（正常吞吐 ≤ 数十次）
limiter = Limiter(key_func=get_remote_address)


@router.post("/feishu")
@limiter.limit("120/minute")
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
    """处理收到的消息事件（员工私聊机器人 / 询问回复）"""
    event = body.get("event", {})
    header = body.get("header", {})
    event_id = header.get("event_id", "")
    message = event.get("message", {})
    sender = event.get("sender", {}) or {}

    msg_type = message.get("message_type", "")
    chat_type = message.get("chat_type", "")
    chat_id = message.get("chat_id", "")
    parent_id = message.get("parent_id", "") or message.get("root_id", "")

    sender_id_obj = sender.get("sender_id", {}) or {}
    open_id = sender_id_obj.get("open_id", "")

    # 只处理私聊文本，群消息忽略
    if chat_type != "p2p" or msg_type != "text":
        return {"code": 0, "msg": "ok"}

    # 去重：用 Redis SETNX
    if event_id:
        try:
            from redis.asyncio import Redis
            from app.config import get_settings
            r = Redis.from_url(get_settings().REDIS_URL)
            ok = await r.set(f"feishu:event:{event_id}", "1", ex=60, nx=True)
            await r.aclose()
            if not ok:
                logger.info(f"重复事件忽略: {event_id}")
                return {"code": 0, "msg": "ok"}
        except Exception as e:
            logger.debug(f"事件去重检查失败（继续处理）: {e}")

    # 提取文本内容
    try:
        content = json.loads(message.get("content", "{}"))
        text = content.get("text", "") or ""
    except Exception:
        text = ""

    if not text or not open_id:
        return {"code": 0, "msg": "ok"}

    logger.info(f"私聊消息: open_id={open_id[:12]}.., text={text[:60]}")

    # 异步处理（不阻塞 webhook 返回，避免飞书 3 秒超时）
    import asyncio
    asyncio.create_task(_process_dm_async(open_id, text, parent_id))

    # 立即 ACK
    return {"code": 0, "msg": "ok"}


async def _process_dm_async(open_id: str, text: str, parent_id: str = ""):
    """后台处理 DM：先尝试匹配询问回复，否则走员工对话Agent"""
    try:
        # 1. 查员工身份
        from sqlalchemy import select
        from app.database import async_session
        from app.models import Employee

        async with async_session() as session:
            r = await session.execute(
                select(Employee).where(Employee.feishu_open_id == open_id)
            )
            emp = r.scalar_one_or_none()

        if not emp:
            from app.services.feishu.messages import send_text
            await send_text(
                receive_id=open_id, receive_id_type="open_id",
                text="未识别身份，请联系管理员把你的飞书账号绑定到员工库。",
            )
            return

        # 2. 是否是询问回复？
        from app.agents.employee_inquiry_graph import process_employee_reply
        reply_result = await process_employee_reply(open_id, text, parent_id)

        from app.services.feishu.messages import send_text

        if reply_result.get("matched"):
            ack = (
                f"✅ 已记录到「{reply_result['project_name']}」时间轴。\n"
                f"进展: {reply_result.get('progress','-')}\n"
            )
            if reply_result.get("blockers"):
                ack += f"阻碍: {reply_result['blockers']}"
            await send_text(receive_id=open_id, receive_id_type="open_id", text=ack)
            return

        # 3. 否则走员工对话Agent
        from app.agents.employee_chat_graph import chat_about_employee
        result = await chat_about_employee(
            employee_id=str(emp.id),
            message=text,
            thread_id=f"dm-{emp.id}",
        )
        reply = result.get("reply", "我理解你的问题，但暂时无法回答。")
        await send_text(receive_id=open_id, receive_id_type="open_id", text=reply)

    except Exception as e:
        logger.error(f"DM处理失败: {e}", exc_info=True)
        try:
            from app.services.feishu.messages import send_text
            await send_text(
                receive_id=open_id, receive_id_type="open_id",
                text=f"处理失败：{e}",
            )
        except Exception:
            pass
