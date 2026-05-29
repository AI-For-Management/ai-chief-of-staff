"""统一UI样式 — 最小化CSS，依赖Streamlit主题"""
import streamlit as st

CUSTOM_CSS = """
<style>
/* 侧边栏深色背景 */
section[data-testid="stSidebar"] {
    background-color: #1e293b !important;
}
/* 侧边栏所有文字纯白 */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] * {
    color: #ffffff !important;
}
</style>
"""


def apply_style():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.divider()


def sidebar_branding():
    from auth import logout_button
    st.sidebar.title("🏢 AI首席参谋")
    st.sidebar.caption("Chief of Staff")
    logout_button()
    st.sidebar.divider()

    # 人事概览
    try:
        import requests
        resp = requests.get("http://fastapi:8000/api/hr/summary", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            st.sidebar.markdown("**👥 团队概览**")
            st.sidebar.markdown(f"在职人数: **{data['total_employees']}**")
            st.sidebar.markdown(f"平均贡献: **{data['avg_contribution']}**")
            st.sidebar.markdown(f"平均完成率: **{data['avg_completion_pct']}%**")
            st.sidebar.markdown(f"平均负荷: **{data['avg_workload']}**")
            st.sidebar.divider()
    except Exception:
        pass
