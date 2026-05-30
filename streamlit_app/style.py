"""统一 UI 样式 — 模块化主题系统

设计目标：玻璃拟态 + 渐变 + 微交互，让 Streamlit 看起来更像专业 SaaS 产品而非内部工具。
所有可调节项集中在 THEME_TOKENS 中，单点修改即可变换主题。
"""
import streamlit as st
from contextlib import contextmanager


# ============================================================
# 主题令牌（单点修改）
# ============================================================
THEME_TOKENS = {
    # 主色（用于按钮、链接、强调）
    "primary": "#3b82f6",
    "primary_dark": "#2563eb",
    "primary_glow": "rgba(59,130,246,0.35)",
    # 渐变端点
    "gradient_from": "#0f172a",
    "gradient_to": "#1e3a8a",
    # 文本
    "text_primary": "#0f172a",
    "text_secondary": "#475569",
    "text_muted": "#94a3b8",
    # 卡片
    "card_bg": "rgba(255,255,255,0.85)",
    "card_border": "rgba(200,210,220,0.45)",
    "card_shadow": "0 8px 28px rgba(15,23,42,0.07)",
    "card_radius": "16px",
    # 侧边栏
    "sidebar_from": "#0f172a",
    "sidebar_to": "#1e293b",
    # 输入框
    "input_focus": "#3b82f6",
    "input_focus_glow": "rgba(59,130,246,0.12)",
}


# ============================================================
# CSS 模块
# ============================================================

CSS_BASE = """
.main .block-container {
    max-width: 1400px;
    padding-top: 1.5rem;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* 字体 */
html, body, [data-testid="stAppViewContainer"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

/* 滚动条 */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: rgba(100,116,139,0.35); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(100,116,139,0.55); }
::-webkit-scrollbar-track { background: transparent; }
"""

CSS_GLASS = """
/* 全局玻璃卡（接管 st.container(border=True)） */
[data-testid="stVerticalBlockBorderWrapper"] > div:first-child {
    background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,255,255,0.78)) !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    border: 1px solid rgba(200,210,220,0.45) !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 28px rgba(15,23,42,0.07) !important;
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"] > div:first-child:hover {
    box-shadow: 0 14px 38px rgba(15,23,42,0.10) !important;
}

/* 自定义 .glass-card 类（可手动写 unsafe_allow_html） */
.glass-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,255,255,0.78));
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(200,210,220,0.45);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    box-shadow: 0 8px 28px rgba(15,23,42,0.07);
    margin-bottom: 1rem;
}
"""

CSS_GRADIENT = """
/* 渐变标题 */
.gradient-title {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    color: transparent;
    font-weight: 700;
    margin: 0 0 0.4rem 0;
}
.gradient-title.h1 { font-size: 2rem; line-height: 1.25; }
.gradient-title.h2 { font-size: 1.4rem; line-height: 1.3; }

/* 主标题（page header） */
.main h1 {
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* Markdown 输出标题字号收敛 */
.main .stMarkdown h1 { font-size: 1.25rem !important; font-weight: 700; margin: 0.6rem 0 0.4rem 0; }
.main .stMarkdown h2 { font-size: 1.1rem !important; font-weight: 600; margin: 0.5rem 0 0.3rem 0; }
.main .stMarkdown h3 { font-size: 1.0rem !important; font-weight: 600; margin: 0.4rem 0 0.2rem 0; }
.main .stMarkdown p, .main .stMarkdown li { font-size: 0.92rem; line-height: 1.7; }
"""

CSS_BUTTON_PRO = """
/* 主按钮（primary） */
.main .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 14px rgba(59,130,246,0.30) !important;
    transition: all 0.2s ease !important;
}
.main .stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 22px rgba(59,130,246,0.40) !important;
}

/* 次按钮 */
.main .stButton > button[kind="secondary"] {
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.main .stButton > button[kind="secondary"]:hover {
    border-color: #3b82f6 !important;
    transform: translateY(-1px) !important;
}

/* 输入框聚焦发光 */
.main .stTextInput input,
.main .stTextArea textarea {
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
}
.main .stTextInput input:focus,
.main .stTextArea textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
}
"""

CSS_SIDEBAR_PRO = """
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] a,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] div {
    color: #ffffff !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.10) !important;
}
/* 侧边栏导航 */
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
    border-radius: 8px !important;
    margin: 2px 6px !important;
    transition: all 0.15s ease !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
    background-color: rgba(59,130,246,0.18) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: rgba(59,130,246,0.30) !important;
    border-left: 3px solid #60a5fa !important;
}
/* 侧边栏按钮 */
section[data-testid="stSidebar"] .stButton > button {
    background-color: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    transition: all 0.18s ease !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(220,38,38,0.85) !important;
    border-color: rgba(220,38,38,1) !important;
    transform: translateY(-1px) !important;
}
"""

CSS_LOGIN = """
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }

/* 纯净深色背景 + 极细网格质感（参考 Linear/Vercel） */
[data-testid="stAppViewContainer"] {
    background: #0a0a0f !important;
    background-image:
        radial-gradient(circle at 20% 20%, rgba(59,130,246,0.08) 0%, transparent 40%),
        radial-gradient(circle at 80% 80%, rgba(99,102,241,0.08) 0%, transparent 40%);
}

.main .block-container {
    max-width: 440px;
    padding-top: 10vh;
}

/* 品牌 Logo mark — 大尺寸方形圆角渐变块 + 光晕 */
.login-brand {
    text-align: center;
    margin-bottom: 3rem;
}
.login-mark {
    position: relative;
    width: 104px;
    height: 104px;
    margin: 0 auto 2rem auto;
    border-radius: 26px;
    background: linear-gradient(135deg, #3b82f6 0%, #6366f1 50%, #8b5cf6 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow:
        0 20px 60px rgba(99,102,241,0.50),
        0 0 0 1px rgba(255,255,255,0.10) inset,
        0 1px 0 rgba(255,255,255,0.25) inset;
    font-size: 3rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
}
/* Logo 外发光光晕 */
.login-mark::before {
    content: "";
    position: absolute;
    inset: -30%;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(99,102,241,0.45) 0%, transparent 65%);
    filter: blur(20px);
    z-index: -1;
}
.login-brand h1 {
    font-size: 2rem;
    font-weight: 800;
    color: #f8fafc;
    margin: 0;
    letter-spacing: -0.02em;
}
.login-brand p {
    color: #64748b;
    font-size: 0.95rem;
    margin: 0.7rem 0 0 0;
}

/* 输入框 — 深色质感 */
.main .stTextInput label {
    color: #94a3b8 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}
.main .stTextInput input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 10px !important;
    color: #f8fafc !important;
    padding: 0.7rem 0.9rem !important;
    transition: all 0.2s ease !important;
}
.main .stTextInput input::placeholder { color: #475569 !important; }
.main .stTextInput input:focus {
    border-color: #3b82f6 !important;
    background: rgba(255,255,255,0.06) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}

/* 登录按钮 — 全宽渐变 */
.main .stButton > button,
.main .stFormSubmitButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.65rem !important;
    color: #ffffff !important;
    box-shadow: 0 4px 14px rgba(59,130,246,0.30) !important;
    transition: all 0.2s ease !important;
    margin-top: 0.5rem !important;
}
.main .stFormSubmitButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 22px rgba(59,130,246,0.45) !important;
}

/* 表单容器无边框（融入背景） */
.main [data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
}
"""

CSS_METRIC = """
/* 指标卡片美化（兼容 streamlit-extras style_metric_cards） */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(248,250,252,0.85));
    border: 1px solid rgba(200,210,220,0.45);
    border-radius: 14px;
    padding: 1.1rem 1.3rem !important;
    box-shadow: 0 4px 18px rgba(15,23,42,0.05);
    transition: all 0.2s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 28px rgba(15,23,42,0.08);
}
[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    color: #64748b !important;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}

/* 聊天消息（在 chat_message 内的 markdown 也限制字号） */
[data-testid="stChatMessage"] .stMarkdown h1 { font-size: 1.2rem !important; }
[data-testid="stChatMessage"] .stMarkdown h2 { font-size: 1.05rem !important; }
[data-testid="stChatMessage"] .stMarkdown h3 { font-size: 1.0rem !important; }

/* 聊天气泡美化 */
[data-testid="stChatMessage"] {
    border-radius: 14px !important;
    padding: 0.4rem 0.6rem !important;
    margin-bottom: 0.4rem !important;
}

/* 带高度的滚动容器（对话框/方案预览）— 玻璃感 + 更柔和边框 */
[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stChatMessage"]) {
    background: rgba(248,250,252,0.6) !important;
    border-radius: 16px !important;
}

/* 标签/徽章 */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-left: 0.4rem;
}
.badge-planning { background: #fef3c7; color: #92400e; }
.badge-progress { background: #dbeafe; color: #1e40af; }
.badge-done     { background: #d1fae5; color: #065f46; }
.badge-paused   { background: #e5e7eb; color: #374151; }

/* tabs 美化 */
.main [data-baseweb="tab-list"] {
    gap: 8px;
}
.main [data-baseweb="tab"] {
    border-radius: 10px 10px 0 0 !important;
    font-weight: 500 !important;
}

/* ===== 对话输入区 composer（参考 ChatGPT / Claude）===== */
.composer-wrap [data-testid="stVerticalBlockBorderWrapper"] > div:first-child {
    background: #ffffff !important;
    border: 1px solid rgba(200,210,220,0.7) !important;
    border-radius: 18px !important;
    box-shadow: 0 6px 24px rgba(15,23,42,0.06) !important;
    padding: 0.4rem 0.6rem !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.composer-wrap [data-testid="stVerticalBlockBorderWrapper"] > div:first-child:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.12) !important;
}
/* composer 内的文本框去边框，融入卡片 */
.composer-wrap .stTextArea textarea {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    font-size: 0.95rem !important;
    resize: none !important;
}
.composer-wrap .stTextArea textarea:focus {
    border: none !important;
    box-shadow: none !important;
}
/* composer 圆形发送按钮（向上箭头） */
.composer-send .stButton > button {
    border-radius: 50% !important;
    width: 40px !important;
    height: 40px !important;
    min-height: 40px !important;
    padding: 0 !important;
    font-size: 1.2rem !important;
    line-height: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
/* composer 内 toggle 垂直居中 */
.composer-tools [data-testid="stToggle"] { margin-top: 0.35rem; }
"""

# ============================================================
# 注入函数
# ============================================================

CUSTOM_CSS_LOGGED_IN = (
    "<style>" + CSS_BASE + CSS_GLASS + CSS_GRADIENT + CSS_BUTTON_PRO +
    CSS_SIDEBAR_PRO + CSS_METRIC + "</style>"
)

CUSTOM_CSS_LOGIN_PAGE = (
    "<style>" + CSS_BASE + CSS_LOGIN + CSS_BUTTON_PRO + "</style>"
)


def apply_style():
    """已登录页面 — 注入完整样式"""
    st.markdown(CUSTOM_CSS_LOGGED_IN, unsafe_allow_html=True)


def apply_login_style():
    """登录页 — 全屏渐变 + 居中卡片"""
    st.markdown(CUSTOM_CSS_LOGIN_PAGE, unsafe_allow_html=True)


# ============================================================
# 公共组件
# ============================================================

def page_header(title: str, subtitle: str = ""):
    """页面标题（带渐变文字）"""
    st.markdown(f'<h1 class="gradient-title h1">{title}</h1>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(
            f'<p style="color:#64748b;font-size:0.92rem;margin:0 0 1.2rem 0;">{subtitle}</p>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<hr style="border:none;border-top:1px solid rgba(200,210,220,0.5);margin:0 0 1.4rem 0;">',
        unsafe_allow_html=True,
    )


def gradient_header(text: str, level: str = "h2"):
    """单独使用渐变文字"""
    st.markdown(f'<div class="gradient-title {level}">{text}</div>', unsafe_allow_html=True)


@contextmanager
def glass_card():
    """玻璃卡片上下文管理器（备用，目前 st.container(border=True) 已自动美化）"""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown('</div>', unsafe_allow_html=True)


def style_metric_cards():
    """启用 streamlit-extras 的 metric cards 美化（如果已安装）"""
    try:
        from streamlit_extras.metric_cards import style_metric_cards as _smc
        _smc(border_left_color="#3b82f6", box_shadow=True)
    except Exception:
        pass  # streamlit-extras 没装就静默跳过


def sidebar_branding():
    """侧边栏品牌 + 概览"""
    from auth import logout_button

    st.sidebar.markdown(
        """
        <div style="padding: 0.6rem 0 0.2rem 0;">
            <div style="font-size:1.4rem;font-weight:800;
                background: linear-gradient(135deg, #ffffff 0%, #94c5ff 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;">
                AI 首席参谋
            </div>
            <div style="color:rgba(255,255,255,0.65);font-size:0.78rem;margin-top:0.2rem;">
                Chief of Staff
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    logout_button()
    st.sidebar.divider()

    # 团队概览
    try:
        import requests
        resp = requests.get("http://fastapi:8000/api/hr/summary", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            st.sidebar.markdown(
                f"""
                <div style="padding:0.6rem 0;">
                    <div style="font-size:0.8rem;color:rgba(255,255,255,0.55);
                        text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.4rem;">
                        团队概览
                    </div>
                    <div style="font-size:0.88rem;line-height:1.9;">
                        在职 <b>{data['total_employees']}</b> 人 ·
                        贡献 <b>{data['avg_contribution']}</b><br>
                        完成率 <b>{data['avg_completion_pct']}%</b> ·
                        负荷 <b>{data['avg_workload']}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.sidebar.divider()
    except Exception:
        pass
