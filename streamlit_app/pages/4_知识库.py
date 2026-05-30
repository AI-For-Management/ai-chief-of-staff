"""知识库 — AI问答（顶层）+ 视图切换 + 拖拽上传"""
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

# 自定义虚框样式（拖拽上传区）
st.markdown(
    """
<style>
.upload-frame {
    border: 2px dashed #94a3b8;
    border-radius: 12px;
    padding: 1.2rem;
    background: #f8fafc;
    margin-top: 0.6rem;
}
.upload-frame:hover { border-color: #3b82f6; background: #f0f7ff; }
</style>
""",
    unsafe_allow_html=True,
)

# ===================== AI问答（顶层主区）=====================
if "kb_qa_history" not in st.session_state:
    st.session_state.kb_qa_history = []

st.subheader("AI 问答", help="基于知识库相关文档（相关度≥40%）综合回答；无相关文档时明确告知")

if st.session_state.kb_qa_history:
    with st.container(height=500):
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

use_strong = st.checkbox(
    "🧠 深度思考（用强模型，回答更全面但慢约 2-3 倍）",
    value=False,
    help="勾选后用 DeepSeek-V4-Pro。默认 V3 快模型已经够用大部分场景。",
)

user_q = st.chat_input("基于知识库提问...（如：公司面临哪些风险？张明远适合派什么任务？）")
if user_q:
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

# ===================== 视图切换按钮组 =====================
st.markdown("&nbsp;", unsafe_allow_html=True)

if "kb_view" not in st.session_state:
    st.session_state.kb_view = "none"

vc1, vc2, vc3 = st.columns([1, 1, 4])
if vc1.button("🔍 语义搜索", use_container_width=True,
               type=("primary" if st.session_state.kb_view == "search" else "secondary")):
    st.session_state.kb_view = "none" if st.session_state.kb_view == "search" else "search"
    st.rerun()
if vc2.button("📚 文档概述", use_container_width=True,
               type=("primary" if st.session_state.kb_view == "overview" else "secondary")):
    st.session_state.kb_view = "none" if st.session_state.kb_view == "overview" else "overview"
    st.rerun()
if st.session_state.kb_qa_history and vc3.button("清空对话"):
    st.session_state.kb_qa_history = []
    st.rerun()

# 语义搜索视图
if st.session_state.kb_view == "search":
    with st.container(border=True):
        sq = st.text_input("查询内容", placeholder="按相关度返回原始文档片段", key="search_q")
        if st.button("搜索", type="primary", key="search_btn") and sq:
            with st.spinner("检索中..."):
                try:
                    r = requests.post(
                        f"{API_BASE}/api/agents/rag/search",
                        params={"query": sq, "top_k": 5},
                        timeout=30,
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

# 文档概述视图（按分类分组）
if st.session_state.kb_view == "overview":
    with st.container(border=True):
        try:
            r = requests.get(
                f"{API_BASE}/api/knowledge/documents",
                params={"limit": 200},
                timeout=15,
            )
            docs = r.json().get("items", [])
        except Exception as e:
            docs = []
            st.error(f"加载失败：{e}")

        if not docs:
            st.info("知识库还是空的。可以先在下方上传文档。")
        else:
            # 按 category 分组
            by_cat = {}
            for d in docs:
                by_cat.setdefault(d.get("category", "未分类"), []).append(d)

            st.caption(f"共 {len(docs)} 篇文档")
            for cat in CATEGORY_ORDER:
                items = by_cat.get(cat, [])
                if not items:
                    continue
                with st.expander(f"📁 {cat}（{len(items)}）", expanded=False):
                    for d in items:
                        col1, col2 = st.columns([5, 2])
                        col1.markdown(f"**{d['title']}** · {d['char_count']} 字 · v{d['version']}")
                        col2.caption(d['last_updated'][:19])
                        st.caption(f"`{d['doc_token']}`")
                        st.divider()
            # 显示其他未在 CATEGORY_ORDER 里的分类
            for cat, items in by_cat.items():
                if cat in CATEGORY_ORDER:
                    continue
                with st.expander(f"📁 {cat}（{len(items)}）", expanded=False):
                    for d in items:
                        st.markdown(f"**{d['title']}** · {d['char_count']} 字 · v{d['version']}")
                        st.caption(f"`{d['doc_token']}` · {d['last_updated'][:19]}")

# ===================== 拖拽上传区（页面底部）=====================
st.markdown("&nbsp;", unsafe_allow_html=True)
st.markdown('<div class="upload-frame">', unsafe_allow_html=True)

st.markdown("**📥 文档导入**")
st.caption("点击或拖动文件到下方区域。支持 .txt / .md（PDF 暂不支持，请先转换）")

if "pending_uploads" not in st.session_state:
    st.session_state.pending_uploads = []  # [{name, bytes, doc_token}]

uploaded_files = st.file_uploader(
    "选择文件",
    type=["txt", "md"],
    accept_multiple_files=True,
    label_visibility="collapsed",
    key="kb_upload_widget",
)

# 把新选择的加入 pending
if uploaded_files:
    existing_names = {p["name"] for p in st.session_state.pending_uploads}
    for f in uploaded_files:
        if f.name not in existing_names:
            st.session_state.pending_uploads.append({
                "name": f.name,
                "bytes": f.getvalue(),
                "doc_token": "",
            })

# 显示已选文件 + 自定义 doc_token
if st.session_state.pending_uploads:
    st.caption(f"待导入 {len(st.session_state.pending_uploads)} 个文件:")
    for i, item in enumerate(st.session_state.pending_uploads):
        c1, c2, c3 = st.columns([3, 3, 1])
        c1.markdown(f"📄 **{item['name']}** ({len(item['bytes'])} 字节)")
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
                    results_log.append(f"✅ {item['name']} → {r.json().get('doc_token','')}")
                else:
                    fail += 1
                    results_log.append(f"❌ {item['name']}: {r.text[:100]}")
            except Exception as e:
                fail += 1
                results_log.append(f"❌ {item['name']}: {e}")
            progress.progress((idx + 1) / total)

        if fail == 0:
            st.success(f"全部 {succ} 个文件导入成功")
        else:
            st.warning(f"成功 {succ}，失败 {fail}")
        with st.expander("查看详情"):
            for r in results_log:
                st.markdown(r)

        # 清空待上传列表
        st.session_state.pending_uploads = []

    if cb2.button("清空待上传"):
        st.session_state.pending_uploads = []
        st.rerun()
else:
    st.caption("尚未选择文件")

st.markdown('</div>', unsafe_allow_html=True)
