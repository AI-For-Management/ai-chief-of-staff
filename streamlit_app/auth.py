"""登录认证模块 — 支持 bcrypt 强密码（生产推荐）+ 旧版 AUTH_USERS（向后兼容）"""
import os
import hashlib
import streamlit as st


# ============================================================
# 密码校验
# ============================================================

def _legacy_sha256(password: str) -> str:
    """旧版 SHA256（保留兼容性）"""
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_bcrypt(password: str, hashed: str) -> bool:
    """用 bcrypt 校验密码"""
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _check_login(username: str, password: str) -> bool:
    """
    认证逻辑：
    1. 优先：admin 用户 + ADMIN_PASSWORD_HASH（bcrypt）
    2. 兼容：AUTH_USERS（用户名:明文密码 列表，SHA256 比对）
    3. 兜底：未配置任何密码 + APP_ENV=development → 接受 admin/admin123
    """
    pwd_hash = (os.getenv("ADMIN_PASSWORD_HASH", "") or "").strip()
    auth_users = (os.getenv("AUTH_USERS", "") or "").strip()
    app_env = (os.getenv("APP_ENV", "development") or "").lower()

    # 1. bcrypt 主路径
    if pwd_hash and username.strip().lower() == "admin":
        return _verify_bcrypt(password, pwd_hash)

    # 2. 旧版 AUTH_USERS
    if auth_users:
        for pair in auth_users.split(","):
            pair = pair.strip()
            if ":" not in pair:
                continue
            u, p = pair.split(":", 1)
            if u.strip() == username.strip() and p.strip() == password:
                return True

    # 3. 开发兜底
    if not pwd_hash and not auth_users and app_env != "production":
        return username.strip() == "admin" and password == "admin123"

    return False


def _check_production_safety() -> str | None:
    """生产模式下检查必备配置；返回错误信息或 None"""
    app_env = (os.getenv("APP_ENV", "development") or "").lower()
    if app_env != "production":
        return None
    if not (os.getenv("ADMIN_PASSWORD_HASH", "") or "").strip():
        return "生产模式下必须配置 ADMIN_PASSWORD_HASH（bcrypt 哈希）"
    return None


# ============================================================
# 登录界面
# ============================================================

def require_login():
    """要求登录。未登录则显示登录表单并阻止后续代码执行。"""
    if st.session_state.get("authenticated"):
        return True

    # 安全配置自检
    err = _check_production_safety()
    if err:
        st.error(f"配置错误：{err}")
        st.stop()

    st.markdown(
        """
        <div class="login-brand">
            <div class="login-mark">AI</div>
            <h1>欢迎回来</h1>
            <p>登录 AI 首席参谋管理平台</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        username = st.text_input("用户名", placeholder="输入用户名")
        password = st.text_input("密码", type="password", placeholder="输入密码")
        submit = st.form_submit_button("登 录", use_container_width=True, type="primary")

        if submit:
            if _check_login(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("用户名或密码错误")

    st.markdown(
        '<p style="text-align:center;color:#475569;'
        'font-size:0.78rem;margin-top:2.5rem;">© 2026 AI Chief of Staff · 企业级智能管理平台</p>',
        unsafe_allow_html=True,
    )
    st.stop()


def logout_button():
    """在侧边栏显示登出按钮"""
    if st.session_state.get("authenticated"):
        st.sidebar.caption(f"当前用户: {st.session_state.get('username', '')}")
        if st.sidebar.button("退出登录", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.rerun()
