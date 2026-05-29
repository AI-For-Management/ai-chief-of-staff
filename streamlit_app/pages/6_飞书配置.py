"""飞书配置 — 应用凭证与资产绑定"""
import streamlit as st
import requests
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from style import apply_style, page_header, sidebar_branding

from auth import require_login
require_login()
apply_style()
sidebar_branding()

API_BASE = "http://fastapi:8000"

def api_get(path):
    return requests.get(f"{API_BASE}{path}", timeout=10).json()
def api_post(path, data):
    return requests.post(f"{API_BASE}{path}", json=data, timeout=10).json()
def api_delete(path):
    return requests.delete(f"{API_BASE}{path}", timeout=10).json()

page_header("飞书配置", "管理飞书应用凭证、绑定多维表格/文档/Wiki/群聊")

st.subheader("应用凭证", help="飞书自建应用的 App ID 与 App Secret，从开放平台后台获取")

with st.expander("添加飞书应用", expanded=False):
    with st.form("add_config"):
        name = st.text_input("配置名称", placeholder="如：正式环境")
        app_id = st.text_input("App ID")
        app_secret = st.text_input("App Secret", type="password")
        encrypt_key = st.text_input("Encrypt Key（选填）")
        verification_token = st.text_input("Verification Token（选填）")

        c1, c2 = st.columns(2)
        test_btn = c1.form_submit_button("测试连通", use_container_width=True)
        save_btn = c2.form_submit_button("保存", use_container_width=True)

        if test_btn and app_id and app_secret:
            result = api_post("/api/admin/lark-configs/test", {"app_id": app_id, "app_secret": app_secret})
            if result.get("status") == "ok":
                st.success(f"连接成功 · Token: {result.get('token_prefix')}")
            else:
                st.error(f"连接失败：{result.get('message')}")

        if save_btn and name and app_id and app_secret:
            try:
                api_post("/api/admin/lark-configs", {
                    "name": name, "app_id": app_id, "app_secret": app_secret,
                    "encrypt_key": encrypt_key, "verification_token": verification_token,
                })
                st.success("已保存")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败：{e}")

# 已有配置列表
try:
    configs = api_get("/api/admin/lark-configs")
    if configs:
        for cfg in configs:
            status = "启用 启用" if cfg['is_active'] else "禁用 禁用"
            with st.container(border=True):
                st.markdown(f"**{cfg['name']}** — `{cfg['app_id'][:16]}...` — {status}")
                if st.button(f"删除此配置", key=f"del_cfg_{cfg['id']}"):
                    api_delete(f"/api/admin/lark-configs/{cfg['id']}")
                    st.rerun()
    else:
        st.info("暂无配置，请添加飞书应用凭证")
except Exception as e:
    st.error(f"加载失败：{e}")

st.divider()

# ===== 资产绑定 =====
st.subheader("资产绑定")
st.caption("绑定多维表格、云文档、Wiki或群聊，AI将自动监控和同步")

with st.expander("添加资产", expanded=False):
    try:
        configs = api_get("/api/admin/lark-configs")
        config_map = {f"{c['name']} ({c['app_id'][:8]}...)": c['id'] for c in configs}
    except Exception:
        config_map = {}

    if not config_map:
        st.warning("请先添加飞书应用凭证")
    else:
        with st.form("add_asset"):
            sel = st.selectbox("关联应用", list(config_map.keys()))
            asset_type = st.selectbox(
                "资产类型",
                ["bitable", "doc", "wiki", "chat"],
                format_func=lambda x: {"bitable": "多维表格", "doc": "云文档", "wiki": "知识库", "chat": "群聊"}[x],
            )
            asset_token = st.text_input("资产Token", placeholder="飞书资源唯一标识")
            asset_name = st.text_input("资产名称", placeholder="方便识别的名称")
            table_id = st.text_input("表ID（多维表格专用）", placeholder="tblXXXX")
            cron = st.text_input("同步频率（Cron表达式）", value="0 */6 * * *")

            if st.form_submit_button("保存", use_container_width=True):
                try:
                    api_post("/api/admin/lark-assets", {
                        "config_id": config_map[sel], "asset_type": asset_type,
                        "asset_token": asset_token, "asset_name": asset_name,
                        "table_id": table_id, "cron_expression": cron,
                    })
                    st.success("已保存")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失败：{e}")

# 已有资产列表
try:
    assets = api_get("/api/admin/lark-assets")
    type_labels = {"bitable": "多维表格", "doc": "云文档", "wiki": "知识库", "chat": "群聊"}
    if assets:
        for a in assets:
            type_str = type_labels.get(a['asset_type'], a['asset_type'])
            name_str = a['asset_name'] or a['asset_token'][:20]
            with st.container(border=True):
                st.markdown(f"**{name_str}** — {type_str} — 同步频率: `{a['cron_expression']}`")
                if st.button(f"删除此资产", key=f"del_a_{a['id']}"):
                    api_delete(f"/api/admin/lark-assets/{a['id']}")
                    st.rerun()
    else:
        st.info("暂无资产绑定")
except Exception as e:
    st.error(f"加载失败：{e}")
