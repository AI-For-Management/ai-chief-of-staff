"""知识库 — AI问答（对话式）+ 文档管理（浏览 / 搜索 / 导入）"""
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

CATEGORY_ORDER = ["情报", "风险", "员工", "项目", "系统", "其他", "未分类"]

page_header("知识库", "公司全部文档的语义中心 — AI综合问答 + 文档浏览 + 一键导入")

# ===================== 状态初始化 =====================
if "kb_qa_history" not in st.session_state:
    st.session_state.kb_qa_history = []
if "kb_pending" not in st.session_state:
    st.session_state.kb_pending = None


def _submit_question():
    """发送按钮回调：把输入暂存到 pending 并清空输入框"""
    text = (st.session_state.get("kb_q_input") or "").strip()
    if text:
        st.session_state.kb_pending = text
        st.session_state.kb_q_input = ""


# ===================== AI问答（主区）=====================
st.subheader("AI 问答", help="基于知识库相关文档（相关度≥40%）综合回答；无相关文档时明确告知")

# 对话历史（滚动容器）
if st.session_state.kb_qa_history:
    with st.container(height=560):
        for msg in st.session_state.kb_qa_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander(f"参考的 {len(msg['sources'])} 篇文档"):
                        for s in msg["sources"]:
                            st.markdown(f"**[文档{s['index']}]** 《{s['title']}》— 相关度 {s['relevance']}%")
                            st.caption(f"`{s['doc_token']}`")
                            st.markdown(s.get("content_preview", ""))
                            st.divider()
else:
    st.info("在下方输入问题开始对话。例如：公司面临哪些风险？张明远适合派什么任务？")

# ---------- 对话输入 composer（文本 + 深度思考 + 发送箭头同一行）----------
st.markdown('<div class="composer-wrap">', unsafe_allow_html=True)
with st.container(border=True):
    st.text_area(
        "提问",
        key="kb_q_input",
        height=80,
        label_visibility="collapsed",
        placeholder="基于知识库提问...（Shift+Enter 换行）",
    )
    tcol, scol = st.columns([6, 1])
    with tcol:
        st.markdown('<div class="composer-tools">', unsafe_allow_html=True)
        use_strong = st.toggle(
            "深度思考",
            key="kb_use_strong",
            help="开启后用 DeepSeek-V4-Pro，回答更全面但慢 2-3 倍；默认快模型已够用",
        )
        st.markdown('</div>', unsafe_allow_html=True)
    with scol:
        st.markdown('<div class="composer-send">', unsafe_allow_html=True)
        st.button("↑", key="kb_send", type="primary",
                  use_container_width=True, on_click=_submit_question)
        st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 清空对话（轻量文字按钮）
if st.session_state.kb_qa_history:
    if st.button("清空对话", key="kb_clear"):
        st.session_state.kb_qa_history = []
        st.rerun()

# ---------- 处理待发送的问题 ----------
if st.session_state.kb_pending:
    user_q = st.session_state.kb_pending
    st.session_state.kb_pending = None
    st.session_state.kb_qa_history.append({"role": "user", "content": user_q})
    spinner_text = "深度思考中（30-60秒）..." if use_strong else "检索并综合中..."
    with st.spinner(spinner_text):
        try:
            resp = requests.post(
                f"{API_BASE}/api/agents/rag/answer",
                json={"query": user_q, "top_k": 8, "threshold": 0.4, "use_strong": use_strong},
                timeout=180,
            )
            data = resp.json()
            answer = data.get("answer", "（无回答）")
            sources = data.get("sources", [])
            st.session_state.kb_qa_history.append({
                "role": "assistant", "content": answer, "sources": sources,
            })
        except Exception as e:
            st.session_state.kb_qa_history.append({
                "role": "assistant", "content": f"提问失败：{e}", "sources": [],
            })
    st.rerun()

# ===================== 文档管理（浏览 / 搜索 / 导入）=====================
st.markdown("&nbsp;", unsafe_allow_html=True)
st.divider()

with st.expander("文档管理 — 浏览 / 语义搜索 / 导入", expanded=False):
    tab_browse, tab_search, tab_upload = st.tabs(["文档浏览", "语义搜索", "导入文档"])

    # ---------- 文档浏览（按分类分组）----------
    with tab_browse:
        try:
            r = requests.get(f"{API_BASE}/api/knowledge/documents",
                             params={"limit": 200}, timeout=15)
            docs = r.json().get("items", [])
        except Exception as e:
            docs = []
            st.error(f"加载失败：{e}")

        if not docs:
            st.info("知识库还是空的。可以在「导入文档」标签上传。")
        else:
            by_cat = {}
            for d in docs:
                by_cat.setdefault(d.get("category", "未分类"), []).append(d)

            st.caption(f"共 {len(docs)} 篇文档")
            ordered = [c for c in CATEGORY_ORDER if by_cat.get(c)]
            ordered += [c for c in by_cat if c not in CATEGORY_ORDER]
            for cat in ordered:
                items = by_cat[cat]
                with st.expander(f"{cat}（{len(items)}）", expanded=False):
                    for d in items:
                        col1, col2 = st.columns([5, 2])
                        col1.markdown(f"**{d['title']}** · {d['char_count']} 字 · v{d['version']}")
                        col2.caption(d['last_updated'][:19])
                        st.caption(f"`{d['doc_token']}`")
                        st.divider()

    # ---------- 语义搜索 ----------
    with tab_search:
        sq = st.text_input("查询内容", placeholder="按相关度返回原始文档片段", key="search_q")
        if st.button("搜索", type="primary", key="search_btn") and sq:
            with st.spinner("检索中..."):
                try:
                    r = requests.post(
                        f"{API_BASE}/api/agents/rag/search",
                        params={"query": sq, "top_k": 5}, timeout=30,
                    )
                    results = r.json().get("results", [])
                    if results:
                        st.success(f"找到 {len(results)} 条")
                        for i, x in enumerate(results, 1):
                            relevance = max(0, 1 - x['distance'])
                            with st.expander(f"{i}. {x['title']}（v{x['version']}）— 相关度 {relevance:.0%}"):
                                st.caption(f"标识: {x['doc_token']} · 更新: {x['last_updated']}")
                                st.markdown(x["content"])
                    else:
                        st.info("未找到相关文档")
                except Exception as e:
                    st.error(f"搜索失败：{e}")

    # ---------- 导入文档 ----------
    with tab_upload:
        st.caption("支持 .txt / .md（PDF 暂不支持，请先转换）")

        if "pending_uploads" not in st.session_state:
            st.session_state.pending_uploads = []  # [{name, bytes, doc_token}]

        uploaded_files = st.file_uploader(
            "选择文件",
            type=["txt", "md"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="kb_upload_widget",
        )

        if uploaded_files:
            existing_names = {p["name"] for p in st.session_state.pending_uploads}
            for f in uploaded_files:
                if f.name not in existing_names:
                    st.session_state.pending_uploads.append({
                        "name": f.name, "bytes": f.getvalue(), "doc_token": "",
                    })

        if st.session_state.pending_uploads:
            st.caption(f"待导入 {len(st.session_state.pending_uploads)} 个文件:")
            for i, item in enumerate(st.session_state.pending_uploads):
                c1, c2, c3 = st.columns([3, 3, 1])
                c1.markdown(f"**{item['name']}** ({len(item['bytes'])} 字节)")
                new_token = c2.text_input(
                    "doc_token (选填)",
                    value=item["doc_token"],
                    key=f"upload_token_{i}",
                    placeholder="如 resume-T001 / meeting-2026-05-30",
                    label_visibility="collapsed",
                )
                st.session_state.pending_uploads[i]["doc_token"] = new_token
                if c3.button("移除", key=f"remove_upload_{i}", use_container_width=True):
                    st.session_state.pending_uploads.pop(i)
                    st.rerun()

            cb1, cb2 = st.columns([1, 4])
            if cb1.button("一键导入", type="primary", use_container_width=True):
                progress = st.progress(0.0)
                succ, fail = 0, 0
                total = len(st.session_state.pending_uploads)
                results_log = []
                for idx, item in enumerate(st.session_state.pending_uploads):
                    try:
                        files = {"file": (item["name"], item["bytes"], "text/plain")}
                        data = {"doc_token": item.get("doc_token") or "", "title": ""}
                        r = requests.post(
                            f"{API_BASE}/api/knowledge/upload",
                            files=files, data=data, timeout=120,
                        )
                        if r.status_code == 200:
                            succ += 1
                            results_log.append(f"成功 {item['name']} → {r.json().get('doc_token','')}")
                        else:
                            fail += 1
                            results_log.append(f"失败 {item['name']}: {r.text[:100]}")
                    except Exception as e:
                        fail += 1
                        results_log.append(f"失败 {item['name']}: {e}")
                    progress.progress((idx + 1) / total)

                if fail == 0:
                    st.success(f"全部 {succ} 个文件导入成功")
                else:
                    st.warning(f"成功 {succ}，失败 {fail}")
                with st.expander("查看详情"):
                    for r in results_log:
                        st.markdown(r)
                st.session_state.pending_uploads = []

            if cb2.button("清空待上传"):
                st.session_state.pending_uploads = []
                st.rerun()
        else:
            st.caption("尚未选择文件")
