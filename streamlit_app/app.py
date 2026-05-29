"""AI Chief of Staff — 管理后台首页"""
import streamlit as st
import requests
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from style import apply_style, page_header, sidebar_branding

st.set_page_config(page_title="AI首席参谋", page_icon="🏢", layout="wide")
from auth import require_login
require_login()
apply_style()
sidebar_branding()

API_BASE = "http://fastapi:8000"

page_header("控制台", "系统运行状态总览")

# 系统状态
try:
    resp = requests.get(f"{API_BASE}/health", timeout=5)
    data = resp.json()
    db_ok = data.get("db") == "ok"
    redis_ok = data.get("redis") == "ok"
except Exception:
    db_ok = redis_ok = False

col1, col2, col3 = st.columns(3)
col1.metric("数据库", "正常" if db_ok else "异常", delta="运行中" if db_ok else "离线")
col2.metric("缓存服务", "正常" if redis_ok else "异常", delta="运行中" if redis_ok else "离线")
col3.metric("系统状态", "全部正常" if (db_ok and redis_ok) else "部分异常")

st.divider()

st.subheader("功能模块")

col1, col2 = st.columns(2)
with col1:
    st.info("**📰 情报简报**\n\n每日自动搜索行业新闻，AI分析后生成结构化简报，自动存入知识库。")
    st.info("**📚 知识管理**\n\n自动监控飞书文档变化，构建可搜索的向量知识库，支持语义检索。")

with col2:
    st.info("**📋 智能规划**\n\nCEO说一句话，AI结合知识库拆解任务，多轮讨论后生成正式文档。")
    st.info("**🚨 风险预警**\n\n每日扫描项目进度和群聊情绪，主动发现风险并推送报告。")
