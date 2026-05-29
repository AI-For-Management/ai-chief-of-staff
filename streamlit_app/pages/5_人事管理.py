"""人事管理 — 排行榜 + 员工列表 + 多维图谱（阶段4）"""
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

page_header("人事管理", "员工档案、贡献排行榜、多维能力图谱")

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
            for emp in employees:
                with st.expander(f"**{emp['name']}** — {emp['department']} · {emp['position']}"):
                    st.caption(f"工号: {emp['employee_id']}")

                    if emp.get("skills"):
                        skills_str = " · ".join(emp["skills"].keys())
                        st.markdown(f"**技能**: {skills_str}")

                    try:
                        detail_resp = requests.get(f"{API_BASE}/api/hr/employees/{emp['id']}", timeout=10)
                        detail = detail_resp.json()
                        metrics = detail.get("metrics", {})
                        profile = detail.get("employee", {}).get("profile_data", {}) if isinstance(detail.get("employee"), dict) else {}

                        if metrics:
                            st.markdown("**最新指标**")
                            for period_name, m in metrics.items():
                                period_label = {"daily": "日", "weekly": "周", "monthly": "月", "yearly": "年"}.get(period_name, period_name)
                                c1, c2, c3, c4 = st.columns(4)
                                c1.metric(f"{period_label}·贡献分", f"{m['contribution_score']:.1f}")
                                c2.metric(f"{period_label}·完成率", f"{m['completion_rate']*100:.0f}%")
                                c3.metric(f"{period_label}·负荷", f"{m['workload_score']:.0f}")
                                c4.metric(f"{period_label}·质量", f"{m['quality_score']:.1f}")
                        else:
                            st.caption("暂无指标数据，将在每日 23:00 自动更新")

                        # 多维图谱（阶段4填充）
                        if profile and isinstance(profile, dict) and profile and not profile.get("error"):
                            st.markdown("**多维能力图谱**")
                            if profile.get("summary"):
                                st.info(profile["summary"])
                            if profile.get("strengths"):
                                st.markdown(f"**优势**: {' · '.join(profile['strengths'])}")
                            if profile.get("weaknesses"):
                                st.markdown(f"**待提升**: {' · '.join(profile['weaknesses'])}")
                            if profile.get("growth_suggestions"):
                                st.markdown(f"**成长建议**: {' · '.join(profile['growth_suggestions'])}")
                            if profile.get("preferred_roles"):
                                st.markdown(f"**适合的角色**: {' · '.join(profile['preferred_roles'])}")
                            if profile.get("skills"):
                                st.markdown("**技能详情**")
                                for s in profile["skills"]:
                                    st.markdown(f"- {s.get('name')} (等级 {s.get('level')})：{s.get('evidence', '')}")
                            st.caption(f"图谱更新于: {profile.get('last_updated', '未知')}")

                        # 触发图谱生成（数据自动从知识库检索，不需手动粘简历）
                        c1, c2 = st.columns([3, 1])
                        c1.caption("提示：员工简历请在「知识库」页上传（doc_token 用 `resume-工号`），生成图谱时会自动关联")
                        if c2.button("更新图谱", key=f"gen_profile_{emp['id']}",
                                      help="基于：基本信息+技能+项目参与+月度指标+知识库自动检索的相关文档"):
                            with st.spinner("AI正在分析多维画像（约30-60秒）..."):
                                try:
                                    r = requests.post(
                                        f"{API_BASE}/api/hr/employees/{emp['id']}/profile/generate",
                                        json={"resume_text": ""},
                                        timeout=300,
                                    )
                                    if r.status_code == 200:
                                        st.success("图谱已生成")
                                        st.rerun()
                                    else:
                                        st.error(f"生成失败：{r.text}")
                                except Exception as e:
                                    st.error(f"生成失败：{e}")
                    except Exception:
                        st.caption("加载详细信息失败")

                    if st.button(f"停用此员工", key=f"del_emp_{emp['id']}",
                                  help="标记为离职，不会真正删除数据"):
                        requests.delete(f"{API_BASE}/api/hr/employees/{emp['id']}", timeout=10)
                        st.rerun()
        else:
            st.info("暂无员工记录")
    except Exception as e:
        st.error(f"加载失败：{e}")
