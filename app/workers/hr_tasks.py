"""HR Agent — 自动分析和维护员工指标"""
import logging
import asyncio
from datetime import datetime, timedelta

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.hr_tasks.update_employee_metrics")
def update_employee_metrics():
    """每日更新员工指标（基于Bitable任务数据）"""
    logger.info("开始更新员工指标")
    try:
        result = asyncio.run(_compute_metrics())
        logger.info(f"员工指标更新完成: {result}")
        return result
    except Exception as e:
        logger.error(f"员工指标更新失败: {e}")
        return {"error": str(e)}


async def _compute_metrics() -> dict:
    """计算所有员工的指标"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.employee import Employee, EmployeeMetrics

    today = datetime.now().strftime("%Y-%m-%d")
    week = datetime.now().strftime("%Y-W%W")
    month = datetime.now().strftime("%Y-%m")
    year = datetime.now().strftime("%Y")

    stats = {"updated": 0, "kb_saved": 0}

    async with async_session() as session:
        result = await session.execute(select(Employee).where(Employee.is_active == True))
        employees = result.scalars().all()

        emp_summaries = []
        for emp in employees:
            # 从Bitable获取任务完成数据
            task_data = await _get_employee_task_data(emp)

            # 计算各项指标
            tasks_completed = task_data.get("completed", 0)
            tasks_assigned = task_data.get("assigned", 0)
            completion_rate = tasks_completed / max(tasks_assigned, 1)
            contribution = _calculate_contribution(tasks_completed, completion_rate, task_data)
            workload = min(100, tasks_assigned * 10)
            quality = task_data.get("quality", 75.0)

            # 写入日指标
            metric = EmployeeMetrics(
                employee_id=emp.id,
                period_type="daily",
                period_date=today,
                tasks_completed=tasks_completed,
                tasks_assigned=tasks_assigned,
                completion_rate=completion_rate,
                contribution_score=contribution,
                workload_score=workload,
                quality_score=quality,
            )
            session.add(metric)
            stats["updated"] += 1

            emp_summaries.append({
                "id": str(emp.id), "name": emp.name, "department": emp.department,
                "completed": tasks_completed, "assigned": tasks_assigned,
                "contribution": contribution, "workload": workload,
            })

        await session.commit()

    # 入库：每日HR摘要
    if emp_summaries:
        try:
            await _save_hr_summary_to_kb(today, emp_summaries)
            stats["kb_saved"] = 1
        except Exception as e:
            logger.error(f"HR摘要入库失败: {e}")

    return stats


async def _save_hr_summary_to_kb(date_str: str, summaries: list):
    """把每日HR摘要存入知识库"""
    import hashlib
    from app.services.rag import upsert_document

    content = f"# 团队工作摘要 {date_str}\n\n"
    content += f"在职人员: {len(summaries)}人\n\n"
    content += "## 各员工今日表现\n\n"

    sorted_summaries = sorted(summaries, key=lambda x: x["contribution"], reverse=True)
    for s in sorted_summaries:
        content += (f"- **{s['name']}** ({s['department']}): "
                    f"完成 {s['completed']}/{s['assigned']} 任务, "
                    f"贡献分 {s['contribution']:.1f}, 负荷 {s['workload']:.0f}\n")

    avg_contribution = sum(s["contribution"] for s in summaries) / len(summaries)
    content += f"\n**团队平均贡献分**: {avg_contribution:.1f}\n"

    await upsert_document(
        doc_token=f"hr-summary-{date_str}",
        title=f"团队工作摘要 {date_str}",
        content=content,
        content_hash=hashlib.md5(content.encode()).hexdigest(),
    )
    logger.info(f"HR摘要已入库: {date_str}")


async def _get_employee_task_data(emp) -> dict:
    """从Bitable获取员工任务数据（如果已绑定）"""
    # 如果飞书未配置，返回默认值
    # 实际使用时会从Bitable读取该员工的任务完成情况
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models import LarkAsset
        from app.services.feishu.bitable import list_records

        async with async_session() as session:
            result = await session.execute(
                select(LarkAsset).where(
                    LarkAsset.asset_type == "bitable",
                    LarkAsset.is_active == True,
                ).limit(1)
            )
            asset = result.scalar_one_or_none()

        if not asset:
            return {"completed": 0, "assigned": 0, "quality": 75.0}

        data = await list_records(asset.asset_token, asset.table_id)
        items = data.get("items", [])

        completed = 0
        assigned = 0
        for item in items:
            fields = item.get("fields", {})
            assignee = str(fields.get("负责人", fields.get("assignee", "")))
            if emp.name in assignee:
                assigned += 1
                status = str(fields.get("状态", fields.get("status", ""))).lower()
                if status in ("done", "完成", "已完成"):
                    completed += 1

        return {"completed": completed, "assigned": assigned, "quality": 75.0 + (completed * 2)}

    except Exception as e:
        logger.debug(f"获取员工 {emp.name} 任务数据失败: {e}")
        return {"completed": 0, "assigned": 0, "quality": 75.0}


def _calculate_contribution(completed: int, rate: float, data: dict) -> float:
    """计算贡献指数 (0-100)"""
    # 公式: 完成数*10 + 完成率*30 + 质量分*0.3
    score = completed * 10 + rate * 30 + data.get("quality", 75) * 0.3
    return min(100, round(score, 1))
