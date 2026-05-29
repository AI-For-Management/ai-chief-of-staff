"""登录认证模块"""
import os
import hashlib
import streamlit as st


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get_users() -> dict:
    """从环境变量加载用户列表，格式: user1:pass1,user2:pass2"""
    users_str = os.getenv("AUTH_USERS", "admin:admin123")
    users = {}
    for pair in users_str.split(","):
        pair = pair.strip()
        if ":" in pair:
            username, password = pair.split(":", 1)
            users[username.strip()] = _hash_password(password.strip())
    return users


def require_login():
    """
    要求登录。未登录则显示登录表单并阻止后续代码执行。
    在每个页面的最顶部调用。
    """
    if st.session_state.get("authenticated"):
        return True

    # 居中logo + 副标题
    st.markdown("""
        <div style="text-align:center; padding:1rem 0 2rem 0;">
            <h1 style="margin:0; font-size:2rem;">AI 首席参谋</h1>
            <p style="color:#64748b; margin:0.5rem 0 0 0;">企业级智能管理平台</p>
        </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("用户名", placeholder="请输入用户名")
        password = st.text_input("密码", type="password", placeholder="请输入密码")
        submit = st.form_submit_button("登录", use_container_width=True, type="primary")

        if submit:
            users = _get_users()
            if username in users and users[username] == _hash_password(password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("用户名或密码错误")

    st.stop()


def logout_button():
    """在侧边栏显示登出按钮"""
    if st.session_state.get("authenticated"):
        st.sidebar.caption(f"当前用户: {st.session_state.get('username', '')}")
        if st.sidebar.button("退出登录", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.rerun()
