"""员工对话 — CEO与AI讨论具体员工的工作"""
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

page_header("员工对话", "选择一位员工，AI 会基于其档案、指标、项目数据回答你的问题")

# 选择员工
try:
    employees = requests.get(f"{API_BASE}/api/hr/employees", timeout=10).json()
except Exception:
    employees = []

if not employees:
    st.warning("暂无员工记录，请先在「人事管理」页面添加员工。")
    st.stop()

emp_options = {f"{e['name']} ({e['department']} · {e['position']})": e for e in employees}

selected_label = st.selectbox(
    "选择员工",
    list(emp_options.keys()),
    help="AI 会加载该员工的全部档案数据后回答你的问题",
)
selected_emp = emp_options[selected_label]

# Session state
if "emp_chat_history" not in st.session_state:
    st.session_state.emp_chat_history = {}
if "emp_chat_thread" not in st.session_state:
    st.session_state.emp_chat_thread = {}

emp_id = selected_emp["id"]
history = st.session_state.emp_chat_history.get(emp_id, [])
thread_id = st.session_state.emp_chat_thread.get(emp_id, "")

st.divider()

# 历史对话
for msg in history:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(msg["content"])

# 输入
user_input = st.chat_input(f"问 AI 关于 {selected_emp['name']} 的问题...")

if user_input:
    history.append({"role": "user", "content": user_input})
    st.session_state.emp_chat_history[emp_id] = history

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("AI 正在分析..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/agents/employees/chat",
                    json={
                        "employee_id": emp_id,
                        "message": user_input,
                        "thread_id": thread_id,
                    },
                    timeout=300,
                )
                data = resp.json()
                reply = data.get("reply", "(无回复)")
                st.session_state.emp_chat_thread[emp_id] = data.get("thread_id", thread_id)
            except Exception as e:
                reply = f"出错: {e}"
            st.markdown(reply)

    history.append({"role": "assistant", "content": reply})
    st.session_state.emp_chat_history[emp_id] = history

# 清空对话
if history:
    if st.button("清空对话", help="清除当前员工的对话历史"):
        st.session_state.emp_chat_history.pop(emp_id, None)
        st.session_state.emp_chat_thread.pop(emp_id, None)
        st.rerun()

# 提示
with st.expander("使用提示"):
    st.markdown("""
    **可以问什么？**
    - "张三最近工作怎么样？建议给他派什么任务？"
    - "他的优势是什么？适合参与哪类项目？"
    - "他和李四谁更适合负责新产品的技术评审？"
    - "对他的下个月工作有什么建议？"

    **AI 会基于以下数据回答：**
    - 员工基本信息（部门、职位、技能）
    - 多维能力图谱（如果已生成）
    - 最近月度工作指标（贡献分、完成率、负荷）
    - 当前正在参与的项目
    """)
