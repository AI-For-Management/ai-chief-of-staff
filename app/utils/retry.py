"""飞书API限流重试装饰器"""
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

logger = logging.getLogger(__name__)


def _is_rate_limit_error(exc: Exception) -> bool:
    """判断是否为飞书429限流错误"""
    exc_str = str(exc)
    return "429" in exc_str or "rate limit" in exc_str.lower() or "too many" in exc_str.lower()


feishu_retry = retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(5),
    before_sleep=lambda rs: logger.warning(f"飞书API限流，{rs.next_action.sleep}秒后重试 (第{rs.attempt_number}次)"),
    reraise=True,
)
