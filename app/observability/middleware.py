"""请求日志中间件 — 注入 request_id 并记录每个请求的结构化日志"""
import time
import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.observability.logging import request_id_ctx

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """为每个请求生成 request_id，写入响应头，并记录耗时/状态码。

    /health* 探活请求只在出错时记录，避免日志被健康检查刷屏。
    """

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        token = request_id_ctx.set(rid)
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            path = request.url.path
            is_health = path.startswith("/health")
            if not is_health or status_code >= 400:
                logger.info(
                    f"{request.method} {path} {status_code} {elapsed_ms}ms",
                    extra={"extra_fields": {
                        "method": request.method,
                        "path": path,
                        "status": status_code,
                        "duration_ms": elapsed_ms,
                    }},
                )
            request_id_ctx.reset(token)
