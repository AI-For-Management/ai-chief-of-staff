"""人事管理 — 排行榜 + 员工列表 + 多维图谱（阶段4）"""
import streamlit as st
import requests
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from style import apply_style, page_header, sidebar_branding, style_metric_cards

from auth import require_login
require_login()
apply_style()
sidebar_branding()

API_BASE = "http://fastapi:8000"

page_header("人事管理", "员工档案、贡献排行榜、多维能力图谱")


def _render_employee_detail(emp):
    """渲染单个员工的详情：基础信息 + 指标 + 能力图谱 + 操作按钮"""
    emp_id = emp["id"]
    st.caption(f"工号：{emp.get('employee_id', '—')}")

    skills = emp.get("skills") or {}
    if skills:
        st.markdown("**技能标签：** " + " · ".join(skills.keys()))

    # 拉取详情（含指标与画像）
    try:
        detail = requests.get(f"{API_BASE}/api/hr/employees/{emp_id}", timeout=10).json()
    except Exception as e:
        st.error(f"加载详情失败：{e}")
        return

    # metrics 按周期分组，优先展示月度，否则取任一可用周期
    all_metrics = detail.get("metrics") or {}
    m = all_metrics.get("monthly") or (next(iter(all_metrics.values()), None) if all_metrics else None)
    if m:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("贡献分", f"{m.get('contribution_score', 0):.1f}")
        m2.metric("完成率", f"{m.get('completion_rate', 0) * 100:.0f}%")
        m3.metric("负荷", f"{m.get('workload_score', 0):.0f}")
        m4.metric("质量", f"{m.get('quality_score', 0):.1f}")

    profile = (detail.get("employee") or {}).get("profile_data") or {}
    if profile:
        if profile.get("summary"):
            st.markdown(f"**画像概述：** {profile['summary']}")
        pc1, pc2 = st.columns(2)
        if profile.get("strengths"):
            pc1.markdown("**优势**\n\n" + "\n".join(f"- {s}" for s in profile["strengths"]))
        if profile.get("weaknesses"):
            pc2.markdown("**待提升**\n\n" + "\n".join(f"- {s}" for s in profile["weaknesses"]))
        if profile.get("growth_suggestions"):
            st.markdown("**成长建议**\n\n" + "\n".join(f"- {s}" for s in profile["growth_suggestions"]))
        if profile.get("preferred_roles"):
            st.markdown("**适合角色：** " + " · ".join(profile["preferred_roles"]))
    else:
        st.info("尚无能力图谱，点击下方「更新图谱」生成。")

    bc1, bc2 = st.columns(2)
    if bc1.button("更新图谱", key=f"profile_{emp_id}", use_container_width=True):
        with st.spinner("AI 正在分析员工画像..."):
            try:
                r = requests.post(
                    f"{API_BASE}/api/hr/employees/{emp_id}/profile/generate",
                    json={"resume_text": ""}, timeout=300,
                )
                if r.status_code == 200:
                    st.success("已更新")
                    st.rerun()
                else:
                    st.error(f"失败：{r.text}")
            except Exception as e:
                st.error(f"失败：{e}")

    if bc2.button("停用此员工", key=f"delete_{emp_id}", use_container_width=True):
        try:
            r = requests.delete(f"{API_BASE}/api/hr/employees/{emp_id}", timeout=10)
            if r.status_code == 200:
                st.success("已停用")
                st.rerun()
            else:
                st.error(f"失败：{r.text}")
        except Exception as e:
            st.error(f"失败：{e}")

# 团队汇总 KPI
try:
    _summary = requests.get(f"{API_BASE}/api/hr/summary", timeout=5).json()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("在职人数", _summary.get("total_employees", 0))
    k2.metric("平均贡献分", _summary.get("avg_contribution", 0))
    k3.metric("平均完成率", f"{_summary.get('avg_completion_pct', 0)}%")
    k4.metric("平均负荷", _summary.get("avg_workload", 0))
    style_metric_cards()
except Exception:
    pass

tab_board, tab_employees = st.tabs(["贡献排行榜", "员工列表"])

# ===== TAB 1: 排行榜 =====
with tab_board:
    period = st.radio(
        "排行周期",
        ["daily", "weekly", "monthly", "yearly"],
        format_func=lambda x: {"daily": "日榜", "weekly": "周榜", "monthly": "月榜", "yearly": "年榜"}[x],
        horizontal=True,
        help="按不同时间维度查看员工贡献排名"
    )

    try:
        resp = requests.get(f"{API_BASE}/api/hr/leaderboard/{period}", timeout=10)
        entries = resp.json()

        if entries:
            for entry in entries:
                rank = entry["rank"]
                rank_label = {1: "第1名", 2: "第2名", 3: "第3名"}.get(rank, f"第{rank}名")
                score = entry["contribution_score"]
                rate = entry["completion_rate"]

                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                    c1.markdown(f"**{rank_label}**")
                    c2.markdown(f"**{entry['name']}** · {entry['department']}")
                    c3.metric("贡献分", f"{score:.1f}")
                    c4.metric("完成率", f"{rate*100:.0f}%")
        else:
            st.info("暂无排行数据。添加员工并录入指标后将显示排行榜。")
    except Exception as e:
        st.info("暂无排行数据。")

# ===== TAB 2: 员工列表 =====
with tab_employees:

    with st.expander("添加员工", expanded=False):
        with st.form("add_emp"):
            c1, c2 = st.columns(2)
            name = c1.text_input("姓名")
            emp_id = c2.text_input("工号", help="员工唯一编号，不可重复")
            c3, c4 = st.columns(2)
            dept = c3.text_input("部门")
            pos = c4.text_input("职位")
            feishu_id = st.text_input("飞书 Open ID（选填）",
                                        help="如填写，可与飞书任务系统关联同步")
            skills_text = st.text_input("技能标签（逗号分隔）",
                                         placeholder="Python, 项目管理, 数据分析",
                                         help="用于员工图谱分析")

            if st.form_submit_button("保存", use_container_width=True, type="primary"):
                if name and emp_id:
                    skills = {}
                    if skills_text:
                        skills = {s.strip(): 80 for s in skills_text.split(",") if s.strip()}
                    try:
                        resp = requests.post(f"{API_BASE}/api/hr/employees", json={
                            "name": name, "employee_id": emp_id,
                            "department": dept, "position": pos,
                            "feishu_open_id": feishu_id, "skills": skills,
                        }, timeout=10)
                        if resp.status_code == 200:
                            st.success("已添加")
                            st.rerun()
                        else:
                            st.error(f"失败：{resp.text}")
                    except Exception as e:
                        st.error(f"失败：{e}")
                else:
                    st.warning("姓名和工号为必填")

    # 员工列表
    try:
        resp = requests.get(f"{API_BASE}/api/hr/employees", timeout=10)
        employees = resp.json()

        if employees:
            # 搜索 + 部门筛选
            sc1, sc2 = st.columns([3, 2])
            keyword = sc1.text_input(
                "搜索员工",
                placeholder="按姓名 / 工号 / 职位 / 技能搜索",
                label_visibility="collapsed",
                key="emp_search",
            ).strip().lower()

            all_depts = sorted({e.get("department") or "未分配" for e in employees})
            dept_filter = sc2.selectbox(
                "部门筛选",
                ["全部部门"] + all_depts,
                label_visibility="collapsed",
                key="emp_dept_filter",
            )

            # 过滤
            def _match(e):
                if dept_filter != "全部部门" and (e.get("department") or "未分配") != dept_filter:
                    return False
                if not keyword:
                    return True
                hay = " ".join([
                    e.get("name", ""), e.get("employee_id", ""),
                    e.get("position", ""), e.get("department", ""),
                    " ".join((e.get("skills") or {}).keys()),
                ]).lower()
                return keyword in hay

            filtered = [e for e in employees if _match(e)]

            # 按部门分组
            by_dept = {}
            for e in filtered:
                by_dept.setdefault(e.get("department") or "未分配", []).append(e)

            if not filtered:
                st.info("没有匹配的员工")

            st.caption(f"共 {len(filtered)} 人，分布在 {len(by_dept)} 个部门")

            # 部门 → 员工 两级展示
            for dept in sorted(by_dept.keys()):
                dept_emps = by_dept[dept]
                st.markdown(f"#### {dept}（{len(dept_emps)} 人）")
                for emp in dept_emps:
                    with st.expander(f"{emp['name']} · {emp['position']}"):
                        _render_employee_detail(emp)
        else:
            st.info("暂无员工记录")
    except Exception as e:
        st.error(f"加载失败：{e}")
