"""LLM服务 — SiliconFlow OpenAI兼容接口封装"""
import logging
from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            api_key=settings.SILICONFLOW_API_KEY,
            base_url=settings.SILICONFLOW_BASE_URL,
        )
    return _client


async def chat(
    messages: list[dict],
    use_strong: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """
    调用LLM对话。

    Args:
        messages: OpenAI格式的消息列表
        use_strong: True用V4-Pro(强), False用V3(快)
        temperature: 温度参数
        max_tokens: 最大输出token数
    """
    settings = get_settings()
    model = settings.LLM_MODEL_STRONG if use_strong else settings.LLM_MODEL_FAST
    client = _get_client()

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


async def chat_simple(
    user_message: str,
    system_prompt: str = "",
    use_strong: bool = False,
) -> str:
    """简化版对话接口"""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})
    return await chat(messages, use_strong=use_strong)


async def chat_json(
    user_message: str,
    system_prompt: str = "",
    use_strong: bool = False,
) -> dict:
    """对话并返回JSON"""
    import json

    full_system = (system_prompt or "") + "\n请严格以JSON格式回复，不要包含```或其他标记，只输出纯JSON。"
    reply = await chat_simple(user_message, system_prompt=full_system, use_strong=use_strong)

    reply = reply.strip()
    if reply.startswith("```"):
        lines = reply.split("\n")
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        reply = "\n".join(lines[start:end])

    return json.loads(reply)
