"""AI Chief of Staff — 登录入口 + 首页综合面板"""
import streamlit as st
import requests
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="AI 首席参谋",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth import require_login
from style import apply_style, apply_login_style, page_header, sidebar_branding

API_BASE = "http://fastapi:8000"

# ===== 登录拦截 =====
if not st.session_state.get("authenticated"):
    apply_login_style()
    require_login()  # 内部 st.stop() 阻止后续渲染
    st.stop()

# ===== 已登录：首页综合面板 =====
apply_style()
sidebar_branding()

page_header("综合面板", f"欢迎回来，{st.session_state.get('username', '')} · {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 系统状态
try:
    resp = requests.get(f"{API_BASE}/health", timeout=5)
    h = resp.json()
    db_ok = h.get("db") == "ok"
    redis_ok = h.get("redis") == "ok"
except Exception:
    db_ok = redis_ok = False

c1, c2, c3 = st.columns(3)
c1.metric("数据库", "正常" if db_ok else "离线", help="PostgreSQL + pgvector 状态")
c2.metric("缓存服务", "正常" if redis_ok else "离线", help="Redis 状态")
c3.metric("整体", "全部就绪" if (db_ok and redis_ok) else "部分异常",
          help="点击左侧栏目进入对应功能")

st.divider()

# 四宫格综合面板
col_left, col_right = st.columns(2)

# === 最新情报简报 ===
with col_left:
    st.subheader("最新情报", help="最近一次生成的行业情报简报，自动来自知识库")
    try:
        # 从知识库找最新的 briefing-* 文档
        resp = requests.post(f"{API_BASE}/api/agents/rag/search",
                              params={"query": "情报简报", "top_k": 1}, timeout=10)
        results = resp.json().get("results", [])
        latest = next((r for r in results if r["doc_token"].startswith("briefing-")), None)
        if latest:
            with st.container(border=True):
                st.markdown(f"**{latest['title']}**")
                st.caption(f"更新时间：{latest['last_updated']}")
                st.markdown(latest["content"][:600] + "...")
                st.page_link("pages/1_情报简报.py", label="查看完整简报 →")
        else:
            st.info("暂无简报，请在「情报简报」页面生成。")
    except Exception:
        st.info("暂无简报。")

# === 项目进展 ===
with col_right:
    st.subheader("进行中的项目", help="正在推进的项目列表与最新进展")
    try:
        projs = requests.get(f"{API_BASE}/api/projects?status=in_progress", timeout=10).json()
        if projs:
            for p in projs[:4]:
                with st.container(border=True):
                    st.markdown(f"**{p['name']}**")
                    st.caption(f"负责人：{p.get('owner_name') or '（待定）'}")
                    events = p.get("timeline_events", [])
                    if events:
                        latest_ev = events[-1]
                        st.markdown(f"最新进展：`{latest_ev.get('time', '')}` {latest_ev.get('event', '')}")
        else:
            st.info("当前没有进行中的项目。")
        st.page_link("pages/2_项目进程.py", label="查看全部项目 →")
    except Exception:
        st.info("项目数据加载中...")

st.divider()

col_l2, col_r2 = st.columns(2)

# === 团队概览 ===
with col_l2:
    st.subheader("团队概览", help="员工指标和贡献排行")
    try:
        summary = requests.get(f"{API_BASE}/api/hr/summary", timeout=5).json()
        a, b, c = st.columns(3)
        a.metric("在职人数", summary.get("total_employees", 0))
        b.metric("平均贡献分", summary.get("avg_contribution", 0))
        c.metric("完成率", f"{summary.get('avg_completion_pct', 0)}%")

        leaderboard = requests.get(f"{API_BASE}/api/hr/leaderboard/monthly", timeout=5).json()
        if leaderboard:
            st.markdown("**本月贡献TOP3**")
            for entry in leaderboard[:3]:
                st.markdown(f"- 第{entry['rank']}名 · **{entry['name']}** · {entry['department']} · {entry['contribution_score']}分")
        st.page_link("pages/5_人事管理.py", label="查看完整人事 →")
    except Exception:
        st.info("数据加载中...")

# === 风险提醒 ===
with col_r2:
    st.subheader("风险提醒", help="最近一次风险扫描的关键提示")
    try:
        resp = requests.post(f"{API_BASE}/api/agents/rag/search",
                              params={"query": "风险报告", "top_k": 1}, timeout=10)
        results = resp.json().get("results", [])
        latest = next((r for r in results if r["doc_token"].startswith("alert-")), None)
        if latest:
            with st.container(border=True):
                st.markdown(f"**{latest['title']}**")
                st.caption(f"扫描时间：{latest['last_updated']}")
                st.markdown(latest["content"][:400] + "...")
        else:
            st.success("当前无风险提醒")
    except Exception:
        st.info("暂无风险数据。")
