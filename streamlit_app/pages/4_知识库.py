"""知识库 — 上传 / AI问答 / 语义搜索 / 分类浏览 / 整理"""
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

page_header("知识库", "公司全部文档的语义搜索中心 + AI综合问答")

CATEGORY_OPTIONS = ["全部", "情报", "风险", "员工", "项目", "系统", "其他", "未分类"]

tab_ask, tab_search, tab_browse, tab_upload, tab_admin = st.tabs([
    "AI问答", "语义搜索", "文档浏览", "上传文档", "知识库管理"
])

# ============= TAB 1: AI 综合回答 =============
with tab_ask:
    st.subheader("AI 综合回答", help="KB管理员基于知识库相关文档（相关度≥40%）综合回答你的问题。无相关文档时会明确告知")

    if "kb_qa_history" not in st.session_state:
        st.session_state.kb_qa_history = []

    if st.session_state.kb_qa_history:
        with st.container(height=700):
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

    user_q = st.chat_input("基于知识库提问...（如：公司面临哪些风险？张明远适合派什么任务？）")
    if user_q:
        st.session_state.kb_qa_history.append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.markdown(user_q)
        with st.chat_message("assistant"):
            with st.spinner("KB管理员检索并综合中..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/api/agents/rag/answer",
                        json={"query": user_q, "top_k": 8, "threshold": 0.4},
                        timeout=300,
                    )
                    data = resp.json()
                    answer = data.get("answer", "（无回答）")
                    sources = data.get("sources", [])
                    st.markdown(answer)
                    if sources:
                        with st.expander(f"参考的 {len(sources)} 篇文档"):
                            for s in sources:
                                st.markdown(f"**[文档{s['index']}]** 《{s['title']}》— 相关度 {s['relevance']}%")
                                st.caption(f"`{s['doc_token']}`")
                                st.markdown(s.get("content_preview", ""))
                                st.divider()
                    st.session_state.kb_qa_history.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    })
                except Exception as e:
                    st.error(f"提问失败：{e}")

    if st.session_state.kb_qa_history:
        if st.button("清空对话"):
            st.session_state.kb_qa_history = []
            st.rerun()

# ============= TAB 2: 语义搜索 =============
with tab_search:
    st.subheader("语义搜索", help="返回原始相关文档列表，按相关度排序")

    query = st.text_input("查询内容", placeholder="例如：上季度产品评审、AI行业动态、张三的能力", key="search_q")

    if st.button("搜索", type="primary", key="search_btn") and query:
        with st.spinner("检索中..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/agents/rag/search",
                    params={"query": query, "top_k": 5},
                    timeout=30,
                )
                results = resp.json().get("results", [])

                if results:
                    st.success(f"找到 {len(results)} 条结果")
                    for i, r in enumerate(results, 1):
                        relevance = max(0, 1 - r['distance'])
                        with st.expander(f"{i}. {r['title']}（v{r['version']}）— 相关度 {relevance:.0%}"):
                            st.caption(f"标识: {r['doc_token']} · 更新: {r['last_updated']}")
                            st.markdown(r["content"])
                else:
                    st.info("未找到相关文档")
            except Exception as e:
                st.error(f"搜索失败：{e}")

# ============= TAB 3: 文档浏览（按分类）=============
with tab_browse:
    st.subheader("文档浏览", help="按分类查看知识库中所有文档")

    category = st.selectbox("分类筛选", CATEGORY_OPTIONS, key="browse_cat")
    filter_cat = "" if category == "全部" else category

    try:
        resp = requests.get(
            f"{API_BASE}/api/knowledge/documents",
            params={"category": filter_cat, "limit": 100},
            timeout=10,
        )
        docs = resp.json().get("items", [])

        if docs:
            st.caption(f"共 {len(docs)} 条")
            for d in docs:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([4, 2, 1])
                    c1.markdown(f"**{d['title']}**")
                    c2.markdown(f"`{d['category']}` · v{d['version']} · {d['char_count']}字")
                    if c3.button("删除", key=f"del_{d['doc_token']}"):
                        try:
                            requests.delete(f"{API_BASE}/api/knowledge/documents/{d['doc_token']}", timeout=10)
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除失败：{e}")
                    st.caption(f"标识：`{d['doc_token']}` · 更新：{d['last_updated'][:19]}")
        else:
            st.info(f"暂无 {category} 分类的文档")
    except Exception as e:
        st.error(f"加载失败：{e}")

# ============= TAB 4: 上传文档 =============
with tab_upload:
    st.subheader("上传文档", help="上传简历、会议纪要、政策文件等到知识库")

    st.caption("支持 .txt 和 .md 文件（PDF 暂不支持，请先转换为 txt）")

    uploaded = st.file_uploader("选择文件", type=["txt", "md"])

    col1, col2 = st.columns(2)
    custom_token = col1.text_input(
        "自定义 doc_token（选填）",
        placeholder="如 resume-{employee_id}, meeting-2026-05-29",
        help="用于关联具体业务，留空则自动生成。员工简历建议用 resume-员工ID 格式",
    )
    custom_title = col2.text_input(
        "文档标题（选填）",
        placeholder="留空则用文件名",
    )

    if uploaded and st.button("上传到知识库", type="primary"):
        with st.spinner("上传 + 浓缩 + 向量化..."):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                data = {"doc_token": custom_token or "", "title": custom_title or ""}
                resp = requests.post(
                    f"{API_BASE}/api/knowledge/upload",
                    files=files,
                    data=data,
                    timeout=60,
                )
                if resp.status_code == 200:
                    r = resp.json()
                    st.success(f"上传成功！doc_token: `{r['doc_token']}` · {r['chars']} 字 · v{r['version']}")
                else:
                    st.error(f"上传失败 [{resp.status_code}]: {resp.text}")
            except Exception as e:
                st.error(f"上传失败：{e}")

    st.divider()
    st.caption("**用途示例**：")
    st.markdown("""
- **员工简历**：`doc_token = resume-{employee_id}`，下次员工图谱生成时会自动检索
- **会议纪要**：`doc_token = meeting-{date}`
- **公司政策**：`doc_token = policy-{name}`
- **行业资料**：`doc_token = industry-{topic}`
""")

# ============= TAB 5: 知识库管理 =============
with tab_admin:
    st.subheader("知识库管理", help="KB管理员Agent：扫描重复文档 + 自动分类")

    if st.button("立即整理知识库", use_container_width=True,
                  help="约 30-60 秒。自动分类 + 找疑似重复"):
        with st.spinner("KB 管理员工作中..."):
            try:
                resp = requests.post(f"{API_BASE}/api/agents/kb/manage", timeout=300)
                data = resp.json()
                st.success(
                    f"完成！分类 {data.get('categorized_count', 0)} 条 · "
                    f"疑似重复 {data.get('duplicates_count', 0)} 对"
                )
                report = data.get("report", "")
                if report:
                    with st.expander("查看完整报告", expanded=True):
                        st.markdown(report)
            except Exception as e:
                st.error(f"失败：{e}")

    st.divider()

    st.markdown("**飞书文档同步**")
    if st.button("扫描所有飞书绑定文档", use_container_width=True,
                  help="拉取飞书绑定的云文档/Wiki，更新到本地知识库"):
        try:
            resp = requests.post(f"{API_BASE}/api/agents/knowledge/scan", timeout=10)
            st.info(f"扫描任务已提交 · ID: {resp.json().get('task_id', '')[:12]}...")
        except Exception as e:
            st.error(f"失败：{e}")

    st.divider()

    st.markdown("**手动重新向量化**")
    doc_token = st.text_input("文档Token", placeholder="排查检索效果时用", key="reembed_token")
    if st.button("重新向量化", key="reembed_btn") and doc_token:
        try:
            resp = requests.post(
                f"{API_BASE}/api/agents/knowledge/reembed",
                params={"doc_token": doc_token},
                timeout=10,
            )
            st.info(f"任务已提交 · ID: {resp.json().get('task_id', '')[:12]}...")
        except Exception as e:
            st.error(f"失败：{e}")
