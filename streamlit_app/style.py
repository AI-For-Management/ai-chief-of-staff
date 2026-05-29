"""统一UI样式"""
import streamlit as st

CUSTOM_CSS_LOGGED_IN = """
<style>
/* ===== 主区域宽度（默认780px太窄，放宽到几乎占满）===== */
.main .block-container {
    max-width: 1400px;
    padding-top: 1.5rem;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* ===== 侧边栏深色背景 + 白字 ===== */
section[data-testid="stSidebar"] {
    background-color: #1e293b !important;
}
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* ===== 侧边栏按钮（解决退出登录看不见的问题）===== */
section[data-testid="stSidebar"] .stButton > button {
    background-color: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    color: #ffffff !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(220,38,38,0.85) !important;
    border-color: rgba(220,38,38,1) !important;
}

/* ===== 页面级标题（page_header 用 st.title）===== */
.main h1 {
    color: #0f172a !important;
    font-size: 1.7rem !important;
    font-weight: 700;
}

/* ===== 主区域内 Markdown 输出的标题缩小（避免AI输出h1过大）===== */
.main .stMarkdown h1 {
    font-size: 1.25rem !important;
    font-weight: 700;
    margin: 0.6rem 0 0.4rem 0 !important;
    color: #0f172a !important;
}
.main .stMarkdown h2 {
    font-size: 1.1rem !important;
    font-weight: 600;
    margin: 0.5rem 0 0.3rem 0 !important;
    color: #1e293b !important;
}
.main .stMarkdown h3 {
    font-size: 1.0rem !important;
    font-weight: 600;
    margin: 0.4rem 0 0.2rem 0 !important;
    color: #334155 !important;
}
.main .stMarkdown h4, .main .stMarkdown h5 {
    font-size: 0.95rem !important;
    font-weight: 600;
    margin: 0.3rem 0 0.2rem 0 !important;
}
.main .stMarkdown p, .main .stMarkdown li {
    font-size: 0.92rem;
    line-height: 1.6;
}

/* ===== 长文滚动容器（用 .scroll-box 类标记的元素）===== */
.scroll-box {
    max-height: 540px;
    overflow-y: auto;
    padding-right: 0.5rem;
}

/* ===== 卡片悬停 ===== */
[data-testid="stContainer"]:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}

/* ===== 聊天消息内的 markdown 也限制字号 ===== */
[data-testid="stChatMessage"] .stMarkdown h1 { font-size: 1.2rem !important; }
[data-testid="stChatMessage"] .stMarkdown h2 { font-size: 1.05rem !important; }
[data-testid="stChatMessage"] .stMarkdown h3 { font-size: 1.0rem !important; }
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


def scroll_container_open(max_height: int = 540):
    """开启一个带滚动条的容器（搭配 scroll_container_close 使用）"""
    st.markdown(
        f'<div class="scroll-box" style="max-height:{max_height}px;">',
        unsafe_allow_html=True,
    )


def scroll_container_close():
    st.markdown('</div>', unsafe_allow_html=True)


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
