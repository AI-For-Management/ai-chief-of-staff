"""统一UI样式"""
import streamlit as st

CUSTOM_CSS_LOGGED_IN = """
<style>
/* 侧边栏深色背景 */
section[data-testid="stSidebar"] {
    background-color: #1e293b !important;
}
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] * {
    color: #ffffff !important;
}
/* 美化页面标题 */
h1, h2, h3 {
    color: #0f172a;
}
/* 卡片悬停效果 */
[data-testid="stContainer"]:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}
</style>
"""

CUSTOM_CSS_LOGIN = """
<style>
/* 登录页：完全隐藏侧边栏 */
section[data-testid="stSidebar"] {
    display: none !important;
}
[data-testid="collapsedControl"] {
    display: none !important;
}
/* 主区域居中 */
.main .block-container {
    max-width: 480px;
    padding-top: 6rem;
}
</style>
"""


def apply_style():
    """已登录后注入样式"""
    st.markdown(CUSTOM_CSS_LOGGED_IN, unsafe_allow_html=True)


def apply_login_style():
    """登录页注入样式（隐藏侧边栏）"""
    st.markdown(CUSTOM_CSS_LOGIN, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.divider()


def sidebar_branding():
    """侧边栏品牌标识 + 概览数据"""
    from auth import logout_button

    st.sidebar.markdown("### AI 首席参谋")
    st.sidebar.caption("企业级智能管理平台")
    logout_button()
    st.sidebar.divider()

    # 实时概览
    try:
        import requests
        resp = requests.get("http://fastapi:8000/api/hr/summary", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            st.sidebar.markdown("**团队概览**")
            st.sidebar.markdown(f"在职人数: **{data['total_employees']}**")
            st.sidebar.markdown(f"平均贡献: **{data['avg_contribution']}**")
            st.sidebar.markdown(f"完成率: **{data['avg_completion_pct']}%**")
            st.sidebar.divider()
    except Exception:
        pass
