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

    # 对话历史（带滚动条）
    if st.session_state.plan_messages:
        with st.container(height=650):
            for msg in st.session_state.plan_messages:
                if msg["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(msg["content"])
                else:
                    with st.chat_message("assistant"):
                        # 长文截断改为完整，因为有滚动条了
                        st.markdown(msg["content"])

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
                        timeout=300,
                    )
                else:
                    resp = requests.post(
                        f"{API_BASE}/api/agents/tasks/revise",
                        json={
                            "thread_id": st.session_state.plan_thread_id,
                            "feedback": user_input,
                        },
                        timeout=300,
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
        with st.spinner("提交派发任务..."):
            try:
                # 异步提交（立即返回）
                resp = requests.post(
                    f"{API_BASE}/api/agents/approve",
                    params={"thread_id": st.session_state.plan_thread_id, "action": "approve"},
                    timeout=10,
                )
                data = resp.json()
                st.session_state.plan_messages.append({
                    "role": "assistant",
                    "content": f"已开始派发（thread_id={st.session_state.plan_thread_id}）。\n\n"
                               f"{data.get('result', '')}\n\n"
                               f"⏳ 完成后此处会显示结果。可以等约 1-2 分钟后**点击下方「刷新结果」按钮**查看。",
                })
                st.session_state.plan_status = "running"  # 进入轮询模式
            except Exception as e:
                st.error(f"提交失败：{e}")
        st.rerun()

    # 派发执行中：提供刷新按钮拉取最终结果
    if st.session_state.plan_status == "running" and st.session_state.plan_thread_id:
        if st.button("🔄 刷新派发结果", use_container_width=True,
                       help="后台异步执行中，点这个查询是否完成"):
            try:
                r = requests.get(
                    f"{API_BASE}/api/agents/tasks/status",
                    params={"thread_id": st.session_state.plan_thread_id},
                    timeout=15,
                )
                d = r.json()
                if d.get("status") == "completed":
                    st.session_state.plan_messages.append({
                        "role": "assistant",
                        "content": f"✅ 派发完成：\n\n{d.get('result', '')}",
                    })
                    st.session_state.plan_status = "idle"
                elif d.get("status") == "failed":
                    st.session_state.plan_messages.append({
                        "role": "assistant",
                        "content": f"❌ 派发失败：{d.get('result', '')}",
                    })
                    st.session_state.plan_status = "idle"
                else:
                    st.info(f"还在执行中... 状态: {d.get('status', 'unknown')}。请稍后再点击。")
            except Exception as e:
                st.error(f"查询失败：{e}")
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
        # 用 height 参数自带滚动条（Streamlit 1.31+ 支持）
        with st.container(border=True, height=750):
            st.markdown(latest)
    else:
        st.info("在左侧输入战略指令开始规划。\n\nAI将结合知识库和最新情报为你拆解任务。")

    if st.session_state.plan_thread_id:
        st.caption(f"会话ID: {st.session_state.plan_thread_id}")
