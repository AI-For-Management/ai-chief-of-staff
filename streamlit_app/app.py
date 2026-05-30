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
from style import apply_style, apply_login_style, page_header, sidebar_branding, style_metric_cards
from error_boundary import error_boundary

API_BASE = "http://fastapi:8000"

# ===== 登录拦截 =====
if not st.session_state.get("authenticated"):
    apply_login_style()
    require_login()  # 内部 st.stop() 阻止后续渲染
    st.stop()

# ===== 已登录：首页综合面板 =====
apply_style()
sidebar_branding()

with error_boundary("综合面板加载出错"):
    page_header("综合面板", f"欢迎回来，{st.session_state.get('username', '')} · {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 系统状态
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        h = resp.json()
        db_ok = h.get("db") == "ok"
        redis_ok = h.get("redis") == "ok"
    except Exception:
        db_ok = redis_ok = False

    # 团队/项目 KPI
    team_count = 0
    active_projects = 0
    try:
        summary = requests.get(f"{API_BASE}/api/hr/summary", timeout=5).json()
        team_count = summary.get("total_employees", 0)
    except Exception:
        pass
    try:
        projs = requests.get(f"{API_BASE}/api/projects?status=in_progress", timeout=5).json()
        active_projects = len(projs) if isinstance(projs, list) else 0
    except Exception:
        pass

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("系统状态", "全部就绪" if (db_ok and redis_ok) else "部分异常",
              help="数据库 + 缓存服务健康度")
    c2.metric("在职人数", team_count, help="当前活跃员工数")
    c3.metric("进行中项目", active_projects, help="status=in_progress 的项目数")
    c4.metric("数据服务", "正常" if (db_ok and redis_ok) else "离线",
              help="PostgreSQL + Redis")
    style_metric_cards()

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
                # 简单分页：每页 4 个
                page_size = 4
                total = len(projs)
                total_pages = (total + page_size - 1) // page_size
                page = st.session_state.get("dashboard_proj_page", 1)
                if page > total_pages:
                    page = total_pages
                start = (page - 1) * page_size
                end = start + page_size

                st.caption(f"共 {total} 个，第 {page}/{total_pages} 页")

                for p in projs[start:end]:
                    with st.container(border=True):
                        st.markdown(f"**{p['name']}**")
                        st.caption(f"负责人：{p.get('owner_name') or '（待定）'}")
                        events = p.get("timeline_events", [])
                        if events:
                            latest_ev = events[-1]
                            st.markdown(f"最新进展：`{latest_ev.get('time', '')}` {latest_ev.get('event', '')}")

                # 分页控件
                if total_pages > 1:
                    pc1, pc2, pc3 = st.columns([1, 2, 1])
                    if pc1.button("← 上一页", disabled=(page == 1), use_container_width=True, key="proj_prev"):
                        st.session_state.dashboard_proj_page = max(1, page - 1)
                        st.rerun()
                    pc2.markdown(f"<div style='text-align:center;padding-top:8px;'>{page} / {total_pages}</div>", unsafe_allow_html=True)
                    if pc3.button("下一页 →", disabled=(page == total_pages), use_container_width=True, key="proj_next"):
                        st.session_state.dashboard_proj_page = min(total_pages, page + 1)
                        st.rerun()
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
        h1, h2 = st.columns([3, 2])
        h1.subheader("风险提醒", help="最近一次风险扫描的关键提示")
        if h2.button("立即扫描", use_container_width=True,
                      help="手动触发风险扫描（预警Agent），完成后此处自动刷新"):
            with st.spinner("扫描中（约 30-60 秒）..."):
                try:
                    # 同步调用风险扫描，等扫完再刷新页面
                    # 注意：alerts/scan 是 Celery delay()，但我们需要同步等待
                    # 简单做法：直接走 alert_graph，但API是POST异步任务
                    # 退而求其次：触发后等10秒强制刷新
                    resp = requests.post(
                        f"{API_BASE}/api/agents/alerts/scan",
                        params={"chat_id": ""},
                        timeout=10,
                    )
                    task_id = resp.json().get("task_id", "")
                    # 轮询等待结果（最多 90 秒）
                    import time
                    for _ in range(30):
                        time.sleep(3)
                        # 通过查 KB 看 alert-* 是否有今天的新文档
                        chk = requests.post(f"{API_BASE}/api/agents/rag/search",
                                             params={"query": "风险报告", "top_k": 1}, timeout=5)
                        rs = chk.json().get("results", [])
                        if rs and rs[0]["doc_token"].startswith("alert-"):
                            # 简单地用日期/时间判断是否是新生成的
                            from datetime import datetime as dt
                            today_prefix = f"alert-{dt.now().strftime('%Y-%m-%d')}"
                            if rs[0]["doc_token"].startswith(today_prefix):
                                st.success("扫描完成")
                                break
                    else:
                        st.info("扫描已提交，结果稍后会显示")
                except Exception as e:
                    st.error(f"扫描失败: {e}")
                st.rerun()

        try:
            resp = requests.post(f"{API_BASE}/api/agents/rag/search",
                                  params={"query": "风险报告", "top_k": 3}, timeout=10)
            results = resp.json().get("results", [])
            # 只保留 alert-* 开头的，按时间倒序
            alerts = [r for r in results if r["doc_token"].startswith("alert-")]
            if alerts:
                latest = alerts[0]
                with st.container(border=True):
                    st.markdown(f"**{latest['title']}**")
                    st.caption(f"扫描时间：{latest['last_updated']}")
                    st.markdown(latest["content"][:400] + ("..." if len(latest["content"]) > 400 else ""))
            else:
                st.success("当前无风险提醒")
        except Exception:
            st.info("暂无风险数据。")
