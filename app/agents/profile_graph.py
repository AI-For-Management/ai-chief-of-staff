"""员工图谱 Agent — 综合分析员工能力画像"""
import logging
import json
from datetime import datetime
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.agents import get_checkpointer_async

logger = logging.getLogger(__name__)


class ProfileState(TypedDict):
    employee_id: str
    employee_name: str
    department: str
    position: str
    skills_input: dict  # 现有skills
    resume_text: str    # 上传的简历文本
    project_history: list  # 参与的项目
    task_metrics: dict  # 历史任务指标
    profile_data: dict  # 输出
    saved_to_kb: bool


async def load_employee_data(state: ProfileState) -> dict:
    """加载员工的所有数据：基本信息 + 项目参与 + 任务指标 + 知识库相关文档（含简历）"""
    from sqlalchemy import select, desc
    from app.database import async_session
    from app.models import Employee, EmployeeMetrics, ProjectMember, Project
    import uuid

    emp_id = uuid.UUID(state["employee_id"])

    async with async_session() as session:
        emp = await session.get(Employee, emp_id)
        if not emp:
            return {"profile_data": {"error": "员工不存在"}}

        # 项目参与历史
        projects = []
        result = await session.execute(
            select(ProjectMember, Project)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(ProjectMember.employee_id == emp_id)
        )
        for member, proj in result.all():
            projects.append({
                "name": proj.name,
                "status": proj.status,
                "role": member.role,
                "responsibilities": member.responsibilities,
            })

        # 最近月度指标
        result = await session.execute(
            select(EmployeeMetrics)
            .where(EmployeeMetrics.employee_id == emp_id, EmployeeMetrics.period_type == "monthly")
            .order_by(desc(EmployeeMetrics.period_date))
            .limit(3)
        )
        metrics_list = result.scalars().all()
        metrics_summary = {
            "recent_months": len(metrics_list),
            "avg_contribution": sum(m.contribution_score for m in metrics_list) / max(len(metrics_list), 1),
            "avg_completion_rate": sum(m.completion_rate for m in metrics_list) / max(len(metrics_list), 1),
            "avg_workload": sum(m.workload_score for m in metrics_list) / max(len(metrics_list), 1),
        }

    # 从知识库自动检索员工相关资料（简历、过往评价、被提及记录）
    extra_resume = ""
    try:
        from app.services.rag import search
        # 用 "员工名 简历 工作记录" 作为查询，检索KB中所有相关文档
        rag_query = f"{emp.name} 简历 工作经历 评价"
        rag_results = await search(rag_query, top_k=8)
        # 只取相关度 >= 0.45 的（避免无关文档干扰）
        relevant = [r for r in rag_results if (1 - r["distance"]) >= 0.45]
        # 排除该员工自己已有的画像（避免循环参考）
        relevant = [r for r in relevant if not r["doc_token"].startswith(f"employee-profile-{state['employee_id']}")]

        if relevant:
            extra_parts = []
            for r in relevant[:5]:
                extra_parts.append(f"《{r['title']}》:\n{r['content'][:600]}")
            extra_resume = "\n\n".join(extra_parts)
    except Exception as e:
        logger.warning(f"RAG 检索员工相关资料失败: {e}")

    # 合并 UI 上传的简历 + 知识库自动检索内容
    user_resume = state.get("resume_text", "") or ""
    combined_resume = user_resume
    if extra_resume:
        combined_resume = (
            (user_resume + "\n\n---\n\n") if user_resume else ""
        ) + f"【知识库相关资料】\n{extra_resume}"

    return {
        "employee_name": emp.name,
        "department": emp.department,
        "position": emp.position,
        "skills_input": emp.skills or {},
        "project_history": projects,
        "task_metrics": metrics_summary,
        "resume_text": combined_resume,
    }


async def analyze_profile(state: ProfileState) -> dict:
    """LLM 综合分析多维图谱"""
    from app.services.llm import chat_json

    skills_str = ", ".join(state["skills_input"].keys()) or "（未填写）"
    projects_text = "\n".join(
        f"- 项目 {p['name']}（{p['status']}）：{p['role']} · {p['responsibilities']}"
        for p in state["project_history"]
    ) or "（暂无项目记录）"

    metrics = state["task_metrics"]
    metrics_str = f"近{metrics['recent_months']}个月：平均贡献分 {metrics['avg_contribution']:.1f}，完成率 {metrics['avg_completion_rate']*100:.0f}%，负荷 {metrics['avg_workload']:.0f}"

    prompt = f"""请综合分析以下员工的多维能力画像，结果以JSON返回。

员工: {state['employee_name']}
部门/职位: {state['department']} / {state['position']}
技能标签: {skills_str}

项目参与:
{projects_text}

工作指标: {metrics_str}

简历内容:
{state['resume_text'][:3000] if state['resume_text'] else '（未上传简历）'}

请返回如下结构的JSON:
{{
  "skills": [{{"name": "技能名", "level": 0-100, "evidence": "证据"}}],
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["待提升1", "待提升2"],
  "preferred_roles": ["适合的角色1", "适合的角色2"],
  "growth_suggestions": ["成长建议1", "成长建议2"],
  "summary": "一段60字左右的整体画像描述"
}}"""

    try:
        profile = await chat_json(prompt, use_strong=True)
        profile["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        return {"profile_data": profile}
    except Exception as e:
        logger.error(f"profile分析失败: {e}")
        return {"profile_data": {"error": str(e), "last_updated": datetime.now().strftime("%Y-%m-%d")}}


async def save_to_kb(state: ProfileState) -> dict:
    """保存图谱到 employees.profile_data 和 知识库"""
    import hashlib
    import uuid
    from sqlalchemy import select
    from app.database import async_session
    from app.models import Employee
    from app.services.rag import upsert_document

    emp_id = uuid.UUID(state["employee_id"])
    profile = state.get("profile_data", {})

    # 1. 写入 employees.profile_data
    async with async_session() as session:
        emp = await session.get(Employee, emp_id)
        if emp:
            emp.profile_data = profile
            await session.commit()

    # 2. 写入知识库
    if profile and not profile.get("error"):
        content_md = f"""# {state['employee_name']} 员工能力画像

**部门/职位**: {state['department']} / {state['position']}

**整体画像**: {profile.get('summary', '')}

**优势**: {', '.join(profile.get('strengths', []))}

**待提升**: {', '.join(profile.get('weaknesses', []))}

**适合的角色**: {', '.join(profile.get('preferred_roles', []))}

**成长建议**: {', '.join(profile.get('growth_suggestions', []))}

**技能详情**:
"""
        for s in profile.get("skills", []):
            content_md += f"- {s.get('name')} (等级 {s.get('level')})：{s.get('evidence', '')}\n"

        try:
            await upsert_document(
                doc_token=f"employee-profile-{state['employee_id']}",
                title=f"{state['employee_name']} 员工能力画像",
                content=content_md,
                content_hash=hashlib.md5(content_md.encode()).hexdigest(),
            )
            return {"saved_to_kb": True}
        except Exception as e:
            logger.error(f"画像入库失败: {e}")

    return {"saved_to_kb": False}


async def build_profile_graph():
    graph = StateGraph(ProfileState)
    graph.add_node("load_employee_data", load_employee_data)
    graph.add_node("analyze_profile", analyze_profile)
    graph.add_node("save_to_kb", save_to_kb)
    graph.add_edge(START, "load_employee_data")
    graph.add_edge("load_employee_data", "analyze_profile")
    graph.add_edge("analyze_profile", "save_to_kb")
    graph.add_edge("save_to_kb", END)
    cp = await get_checkpointer_async()
    return graph.compile(checkpointer=cp)


async def generate_profile(employee_id: str, resume_text: str = "") -> dict:
    """对外接口：为员工生成或更新画像"""
    import uuid
    graph = await build_profile_graph()
    thread_id = f"profile-{employee_id[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    state = {
        "employee_id": employee_id,
        "employee_name": "", "department": "", "position": "",
        "skills_input": {}, "resume_text": resume_text,
        "project_history": [], "task_metrics": {},
        "profile_data": {}, "saved_to_kb": False,
    }
    result = await graph.ainvoke(state, config=config)
    return result.get("profile_data", {})
