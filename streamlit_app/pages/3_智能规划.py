"""智能规划 — 多轮对话式任务拆解"""
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

page_header("智能规划", "你说一句战略意图，AI结合知识库和项目数据多轮讨论后派发执行")

# 初始化会话状态
if "plan_messages" not in st.session_state:
    st.session_state.plan_messages = []
if "plan_thread_id" not in st.session_state:
    st.session_state.plan_thread_id = ""
if "plan_status" not in st.session_state:
    st.session_state.plan_status = "idle"

# ===== 左侧对话 + 右侧方案 =====
chat_col, plan_col = st.columns([1, 1], gap="large")

with chat_col:
    st.subheader("与AI讨论", help="多轮对话式规划：先描述战略意图，然后根据AI生成的方案提修改意见，反复迭代直至满意。")

    # 对话历史
    for msg in st.session_state.plan_messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"][:2000])

    # 输入
    user_input = st.text_area(
        "输入指令或修改意见",
        placeholder="例如：下个月要上线新产品线，请安排落实\n或者：把第3个任务截止日期改为下周五",
        height=80,
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        send = st.button("发送", type="primary", use_container_width=True,
                          help="将左侧文本发给AI，首次为初稿，后续为修订。")
    with c2:
        approve = st.button("批准派发", use_container_width=True,
                             help="对当前方案批准，触发飞书Bitable写入和任务创建。")
    with c3:
        reset = st.button("新对话", use_container_width=True,
                           help="清空当前会话，开始新的规划。")

    if send and user_input:
        st.session_state.plan_messages.append({"role": "user", "content": user_input})

        with st.spinner("AI正在分析并规划..."):
            try:
                if st.session_state.plan_status == "idle":
                    resp = requests.post(
                        f"{API_BASE}/api/agents/tasks/decompose",
                        json={"user_input": user_input},
                        timeout=120,
                    )
                else:
                    resp = requests.post(
                        f"{API_BASE}/api/agents/tasks/revise",
                        json={
                            "thread_id": st.session_state.plan_thread_id,
                            "feedback": user_input,
                        },
                        timeout=120,
                    )

                data = resp.json()
                st.session_state.plan_thread_id = data.get("thread_id", st.session_state.plan_thread_id)
                st.session_state.plan_status = data.get("status", "waiting_approval")

                ai_reply = data.get("message", data.get("result", "方案已生成，请查看右侧。"))
                st.session_state.plan_messages.append({"role": "assistant", "content": ai_reply})
            except Exception as e:
                st.session_state.plan_messages.append({"role": "assistant", "content": f"出错了：{e}"})

        st.rerun()

    if approve and st.session_state.plan_thread_id:
        with st.spinner("正在派发任务..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/agents/approve",
                    params={"thread_id": st.session_state.plan_thread_id, "action": "approve"},
                    timeout=60,
                )
                data = resp.json()
                st.session_state.plan_messages.append({
                    "role": "assistant",
                    "content": f"已批准派发。{data.get('result', '')}",
                })
                st.session_state.plan_status = "idle"
            except Exception as e:
                st.error(f"操作失败：{e}")
        st.rerun()

    if reset:
        st.session_state.plan_messages = []
        st.session_state.plan_thread_id = ""
        st.session_state.plan_status = "idle"
        st.rerun()

with plan_col:
    st.subheader("当前方案", help="AI生成的最新方案预览。批准后会写入飞书。")

    ai_msgs = [m for m in st.session_state.plan_messages if m["role"] == "assistant"]
    if ai_msgs:
        latest = ai_msgs[-1]["content"]
        with st.container(border=True):
            st.markdown(latest)
    else:
        st.info("在左侧输入战略指令开始规划。\n\nAI将结合知识库和最新情报为你拆解任务。")

    if st.session_state.plan_thread_id:
        st.caption(f"会话ID: {st.session_state.plan_thread_id}")
