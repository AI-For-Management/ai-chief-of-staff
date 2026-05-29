"""情报简报 — 生成与查看"""
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

page_header("📰 情报简报", "搜索行业新闻，AI分析生成结构化简报，自动存入知识库")

st.subheader("搜索话题")
default_topics = "AI行业动态\n半导体产业\n科技公司"
topics_text = st.text_area("每行输入一个话题", value=default_topics, height=100)
chat_id = st.text_input("飞书推送群ID（选填，留空不发送）", placeholder="oc_xxxxx")

col1, col2 = st.columns(2)
with col1:
    generate = st.button("🚀 立即生成", type="primary", use_container_width=True)
with col2:
    async_gen = st.button("⏰ 后台异步执行", use_container_width=True)

if generate:
    topics = [t.strip() for t in topics_text.strip().split("\n") if t.strip()]
    if not topics:
        st.warning("请至少输入一个话题")
    else:
        with st.spinner("正在抓取新闻并生成简报，请稍候..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/agents/briefing",
                    json={"topics": topics, "send_to_chat_id": chat_id},
                    timeout=120,
                )
                data = resp.json()
                sent_text = "已推送飞书" if data.get("sent") else "未推送"
                st.success(f"简报生成完成！话题 {data.get('topic_count', 0)} 个 · {sent_text}")
                st.divider()
                st.markdown(data.get("content", ""))
            except Exception as e:
                st.error(f"生成失败：{e}")

if async_gen:
    topics = [t.strip() for t in topics_text.strip().split("\n") if t.strip()]
    try:
        resp = requests.post(
            f"{API_BASE}/api/agents/briefing/async",
            json={"topics": topics, "send_to_chat_id": chat_id},
            timeout=10,
        )
        data = resp.json()
        st.info(f"任务已提交后台执行 · 任务ID: {data.get('task_id', '')[:12]}...")
    except Exception as e:
        st.error(f"提交失败：{e}")
