"""知识库 — 语义搜索与文档同步"""
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

page_header("知识库", "公司全部文档的语义搜索中心，包含飞书文档、情报简报、风险报告、员工档案")

# ===== 搜索 =====
st.subheader("语义搜索", help="基于向量相似度的语义检索，支持自然语言提问")

query = st.text_input("查询内容", placeholder="例如：上季度产品评审结论、最近的风险提醒、员工张三的能力画像",
                      help="输入任何描述，AI会理解语义找出最相关的文档片段。")

if st.button("搜索", type="primary",
              help="向量检索Top 5结果，按相关度排序") and query:
    with st.spinner("语义检索中..."):
        try:
            resp = requests.post(
                f"{API_BASE}/api/agents/rag/search",
                params={"query": query, "top_k": 5},
                timeout=30,
            )
            data = resp.json()
            results = data.get("results", [])

            if results:
                st.success(f"找到 {len(results)} 条相关文档")
                for i, r in enumerate(results, 1):
                    relevance = max(0, 1 - r['distance'])
                    with st.expander(f"{i}. {r['title']}（v{r['version']}）— 相关度 {relevance:.0%}"):
                        st.caption(f"文档标识: {r['doc_token']} · 更新时间: {r['last_updated']}")
                        st.markdown(r["content"])
            else:
                st.info("未找到相关文档。请先绑定飞书文档并运行扫描，或让Agent充实知识库。")
        except Exception as e:
            st.error(f"搜索失败：{e}")

st.divider()

# ===== 文档同步 =====
st.subheader("文档同步", help="把飞书绑定的文档抓取到本地知识库并生成向量")

if st.button("扫描所有已绑定文档", use_container_width=True,
              help="触发后台任务，遍历飞书配置中的所有文档/Wiki，对变更内容重新向量化"):
    try:
        resp = requests.post(f"{API_BASE}/api/agents/knowledge/scan", timeout=10)
        st.info(f"扫描任务已提交 · ID: {resp.json().get('task_id', '')[:12]}...")
    except Exception as e:
        st.error(f"失败：{e}")

st.divider()

st.subheader("手动重新向量化", help="对单个文档重新生成向量，用于排查检索效果")
doc_token = st.text_input("文档Token", placeholder="输入飞书文档ID或本地doc_token")
if st.button("重新向量化") and doc_token:
    try:
        resp = requests.post(
            f"{API_BASE}/api/agents/knowledge/reembed",
            params={"doc_token": doc_token},
            timeout=10,
        )
        st.info(f"任务已提交 · ID: {resp.json().get('task_id', '')[:12]}...")
    except Exception as e:
        st.error(f"失败：{e}")
