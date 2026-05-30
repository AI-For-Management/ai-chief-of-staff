"""Streamlit 错误兜底 — 捕获页面渲染异常，显示友好提示并上报 Sentry"""
import os
import traceback
from contextlib import contextmanager

import streamlit as st

_SENTRY_READY = False


def _init_sentry_once():
    """惰性初始化 Sentry（DSN 为空则跳过）"""
    global _SENTRY_READY
    if _SENTRY_READY:
        return
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=dsn,
                environment=os.getenv("APP_ENV", "development"),
                traces_sample_rate=0.0,
            )
        except Exception:
            pass
    _SENTRY_READY = True


@contextmanager
def error_boundary(title: str = "页面加载出错"):
    """包裹页面主体；异常时显示友好错误页而非红色堆栈，并上报 Sentry。"""
    _init_sentry_once()
    try:
        yield
    except Exception as e:
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
        except Exception:
            pass

        st.error(f"{title}：{e}")
        st.caption("已记录该错误。可刷新页面重试，或联系系统管理员。")
        with st.expander("技术细节（供排查）"):
            st.code(traceback.format_exc())
        st.stop()
