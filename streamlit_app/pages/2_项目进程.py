"""项目进程 — 项目列表 + 时间轴 + 成员管理"""
import streamlit as st
import requests
import sys, os
from datetime import datetime, date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from style import apply_style, page_header, sidebar_branding
from auth import require_login

require_login()
apply_style()
sidebar_branding()

API_BASE = "http://fastapi:8000"

STATUS_LABELS = {"planning": "规划中", "in_progress": "进行中", "done": "已完成", "paused": "已暂停"}
STATUS_COLORS = {"planning": "[规划]", "in_progress": "[进行]", "done": "[完成]", "paused": "[暂停]"}


def api_get(path):
    return requests.get(f"{API_BASE}{path}", timeout=10).json()
def api_post(path, data):
    return requests.post(f"{API_BASE}{path}", json=data, timeout=10).json()
def api_patch(path, data):
    return requests.patch(f"{API_BASE}{path}", json=data, timeout=10).json()
def api_delete(path):
    return requests.delete(f"{API_BASE}{path}", timeout=10).json()


page_header("项目进程", "管理公司各项目的进度、成员和里程碑",)

# 加载员工列表（用于选择负责人/成员）
try:
    employees = requests.get(f"{API_BASE}/api/hr/employees", timeout=10).json()
except Exception:
    employees = []
emp_map = {f"{e['name']} ({e['department']})": e['id'] for e in employees}


# ===== 创建新项目 =====
with st.expander("创建新项目", expanded=False):
    with st.form("new_project"):
        c1, c2 = st.columns([2, 1])
        name = c1.text_input("项目名称", help="给这个项目起一个清晰的名字")
        owner_label = c2.selectbox("负责人", ["（待定）"] + list(emp_map.keys()),
                                    help="项目最终责任人")

        desc = st.text_area("项目简介", height=80, help="一句话说明项目目标和背景")

        c3, c4 = st.columns(2)
        start_d = c3.date_input("开始日期", value=date.today())
        end_d = c4.date_input("预计结束", value=date.today())

        st.markdown("**关键里程碑**（每行一个，格式：日期|标题）")
        ms_text = st.text_area("里程碑列表", placeholder="2026-06-15|需求评审完成\n2026-07-01|内测上线",
                                height=100, label_visibility="collapsed")

        st.markdown("**项目成员**")
        member_text = st.text_area(
            "成员列表",
            placeholder="选择员工后填写，每行一个：员工名|角色|负责工作\n张三|技术负责人|后端开发\n李四|产品经理|需求梳理",
            height=80, label_visibility="collapsed",
        )

        if st.form_submit_button("创建项目", use_container_width=True, type="primary"):
            if not name:
                st.warning("请填写项目名称")
            else:
                # 解析里程碑
                milestones = []
                for line in ms_text.strip().split("\n"):
                    if "|" in line:
                        d, t = line.split("|", 1)
                        milestones.append({"date": d.strip(), "title": t.strip(), "status": "pending"})

                # 解析成员
                members = []
                emp_name_to_id = {e['name']: e['id'] for e in employees}
                for line in member_text.strip().split("\n"):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 1 and parts[0] in emp_name_to_id:
                        members.append({
                            "employee_id": emp_name_to_id[parts[0]],
                            "role": parts[1] if len(parts) > 1 else "",
                            "responsibilities": parts[2] if len(parts) > 2 else "",
                        })

                payload = {
                    "name": name, "description": desc, "status": "planning",
                    "start_date": datetime.combine(start_d, datetime.min.time()).isoformat(),
                    "end_date": datetime.combine(end_d, datetime.min.time()).isoformat(),
                    "milestones": milestones, "members": members,
                }
                if owner_label != "（待定）":
                    payload["owner_id"] = emp_map[owner_label]

                try:
                    r = requests.post(f"{API_BASE}/api/projects", json=payload, timeout=15)
                    if r.status_code == 200:
                        st.success("项目已创建")
                        st.rerun()
                    else:
                        st.error(f"创建失败：{r.text}")
                except Exception as e:
                    st.error(f"创建失败：{e}")

st.divider()

# ===== 项目列表 =====
st.subheader("项目列表")

try:
    projects = api_get("/api/projects")
except Exception as e:
    projects = []
    st.error(f"加载项目失败：{e}")

if not projects:
    st.info("暂无项目，点击上方「创建新项目」添加。")
else:
    for p in projects:
        status_label = STATUS_LABELS.get(p["status"], p["status"])
        status_icon = STATUS_COLORS.get(p["status"], "⚪")

        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 2, 2])
            c1.markdown(f"### {p['name']}")
            c2.markdown(f"**负责人**: {p.get('owner_name') or '（待定）'}")
            c3.markdown(f"{status_icon} **{status_label}**")

            if p["description"]:
                st.caption(p["description"])

            with st.expander("详情", expanded=False):
                # 成员
                st.markdown("**项目成员**")
                if p.get("members"):
                    for m in p["members"]:
                        st.markdown(f"- **{m['employee_name']}** · {m['role']} · {m['responsibilities']}")
                else:
                    st.caption("暂无成员")

                # 里程碑
                st.markdown("**关键里程碑**")
                for ms in p.get("milestones", []):
                    st.markdown(f"- `{ms.get('date', '')}` · {ms.get('title', '')} · {ms.get('status', 'pending')}")

                # 时间轴
                st.markdown("**进展时间轴**")
                events = p.get("timeline_events", [])
                if events:
                    for e in reversed(events[-10:]):
                        st.markdown(f"- `{e.get('time', '')}` · {e.get('event', '')} · {e.get('author', '')}")
                else:
                    st.caption("暂无进展记录")

                # 添加进展
                with st.form(f"add_event_{p['id']}"):
                    new_event = st.text_input("添加进展", placeholder="例如：完成原型设计评审", key=f"ev_{p['id']}")
                    author = st.text_input("记录人", placeholder="选填", key=f"au_{p['id']}")
                    c1, c2, c3 = st.columns(3)
                    if c1.form_submit_button("添加进展", use_container_width=True):
                        if new_event:
                            api_post(f"/api/projects/{p['id']}/timeline", {"event": new_event, "author": author})
                            st.rerun()
                    new_status = c2.selectbox("修改状态", list(STATUS_LABELS.keys()),
                                                index=list(STATUS_LABELS.keys()).index(p["status"]),
                                                format_func=lambda x: STATUS_LABELS[x],
                                                key=f"st_{p['id']}", label_visibility="collapsed")
                    if c2.form_submit_button("更新状态", use_container_width=True):
                        api_patch(f"/api/projects/{p['id']}", {"status": new_status})
                        st.rerun()
                    if c3.form_submit_button("删除项目", use_container_width=True, type="secondary"):
                        api_delete(f"/api/projects/{p['id']}")
                        st.rerun()
