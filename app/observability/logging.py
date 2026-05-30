"""结构化 JSON 日志

把标准 logging 输出改成单行 JSON，便于 docker logs 采集到 ELK/Loki 等系统。
每条日志携带时间、级别、logger 名、消息；若在请求上下文内，还带 request_id。
"""
import json
import logging
import sys
import contextvars
from datetime import datetime, timezone

# 请求级上下文：middleware 设置 request_id，logger 自动带上
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class JsonFormatter(logging.Formatter):
    """把 LogRecord 序列化为单行 JSON"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        rid = request_id_ctx.get()
        if rid:
            payload["request_id"] = rid

        # 额外结构化字段（logger.info(..., extra={"extra_fields": {...}})）
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def setup_json_logging(level: str = "INFO") -> None:
    """把 root logger 的 handler 换成 JSON 格式输出到 stdout。

    幂等：重复调用只保留一个 JSON handler。
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 移除已有 handler，避免重复/双格式
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    # uvicorn 自带的 logger 交给 root 处理，统一格式
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
