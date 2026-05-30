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


async def _load_all_bitable_records() -> list:
    """一次性拉取所有已绑定 bitable 的全部记录（避免N+1查询）"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import LarkAsset
    from app.services.feishu.bitable import list_records

    async with async_session() as session:
        result = await session.execute(
            select(LarkAsset).where(
                LarkAsset.asset_type == "bitable",
                LarkAsset.is_active == True,
            )
        )
        assets = result.scalars().all()

    all_records = []
    for asset in assets:
        try:
            data = await list_records(asset.asset_token, asset.table_id)
            items = data.get("items", [])
            all_records.extend(items)
            logger.info(f"Bitable {asset.asset_name}: 拉取 {len(items)} 条记录")
        except Exception as e:
            logger.warning(f"拉取 Bitable {asset.asset_name} 失败: {e}")

    return all_records


def _aggregate_employee_tasks(employee_name: str, records: list) -> dict:
    """从内存中的全部记录里筛出某员工的任务统计"""
    completed = 0
    assigned = 0
    for item in records:
        fields = item.get("fields", {})
        assignee = str(fields.get("负责人", fields.get("assignee", "")))
        if employee_name in assignee:
            assigned += 1
            status = str(fields.get("状态", fields.get("status", ""))).lower()
            if status in ("done", "完成", "已完成"):
                completed += 1
    quality = 75.0 + (completed * 2)
    return {"completed": completed, "assigned": assigned, "quality": quality}


async def _compute_metrics() -> dict:
    """计算所有员工的指标（优化版：只拉一次 Bitable，且按周期 upsert 去重）"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.employee import Employee, EmployeeMetrics

    today = datetime.now().strftime("%Y-%m-%d")

    stats = {"updated": 0, "kb_saved": 0}

    # 一次性拉取所有 Bitable 记录
    all_records = await _load_all_bitable_records()

    async with async_session() as session:
        result = await session.execute(select(Employee).where(Employee.is_active == True))
        employees = result.scalars().all()

        emp_summaries = []
        for emp in employees:
            task_data = _aggregate_employee_tasks(emp.name, all_records)

            tasks_completed = task_data["completed"]
            tasks_assigned = task_data["assigned"]
            completion_rate = tasks_completed / max(tasks_assigned, 1)
            contribution = _calculate_contribution(tasks_completed, completion_rate, task_data)
            workload = min(100, tasks_assigned * 10)
            quality = task_data["quality"]

            # UPSERT：如果今天已有该员工的 daily 指标，更新；否则插入
            existing = await session.execute(
                select(EmployeeMetrics).where(
                    EmployeeMetrics.employee_id == emp.id,
                    EmployeeMetrics.period_type == "daily",
                    EmployeeMetrics.period_date == today,
                )
            )
            metric = existing.scalar_one_or_none()
            if metric:
                metric.tasks_completed = tasks_completed
                metric.tasks_assigned = tasks_assigned
                metric.completion_rate = completion_rate
                metric.contribution_score = contribution
                metric.workload_score = workload
                metric.quality_score = quality
            else:
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

    if emp_summaries:
        try:
            await _save_hr_summary_to_kb(today, emp_summaries)
            stats["kb_saved"] = 1
        except Exception as e:
            logger.error(f"HR摘要入库失败: {e}")

    return stats


async def _save_hr_summary_to_kb(date_str: str, summaries: list):
    """把每日HR摘要存入知识库 — 用 LLM 生成人才分析师视角的摘要"""
    import hashlib
    from app.services.rag import upsert_document
    from app.services.llm import chat_simple
    from app.agents.prompts import hr_summary_prompt

    # 数据先组织成结构化文本
    sorted_summaries = sorted(summaries, key=lambda x: x["contribution"], reverse=True)
    avg_contribution = sum(s["contribution"] for s in summaries) / len(summaries)

    raw_data = f"日期: {date_str}\n在职人员: {len(summaries)}人\n平均贡献分: {avg_contribution:.1f}\n\n"
    raw_data += "员工数据:\n"
    for s in sorted_summaries:
        raw_data += (
            f"- {s['name']}（{s['department']}）: "
            f"完成 {s['completed']}/{s['assigned']} 任务, "
            f"贡献分 {s['contribution']:.1f}, 负荷 {s['workload']:.0f}\n"
        )

    # LLM 生成有温度的摘要
    try:
        ai_summary = await chat_simple(
            f"基于以下原始数据，生成今日团队效能摘要：\n\n{raw_data}",
            system_prompt=hr_summary_prompt(),
            use_strong=False,
        )
    except Exception as e:
        logger.warning(f"HR LLM 摘要失败，回退原始数据: {e}")
        ai_summary = ""

    # 最终内容 = LLM摘要 + 原始数据（双轨保留，便于追溯）
    if ai_summary:
        content = f"# 团队工作摘要 {date_str}\n\n{ai_summary}\n\n---\n## 原始数据\n{raw_data}"
    else:
        content = f"# 团队工作摘要 {date_str}\n\n{raw_data}"

    await upsert_document(
        doc_token=f"hr-summary-{date_str}",
        title=f"团队工作摘要 {date_str}",
        content=content,
        content_hash=hashlib.md5(content.encode()).hexdigest(),
    )
    logger.info(f"HR摘要已入库: {date_str}")


def _calculate_contribution(completed: int, rate: float, data: dict) -> float:
    """计算贡献指数 (0-100)"""
    score = completed * 10 + rate * 30 + data.get("quality", 75) * 0.3
    return min(100, round(score, 1))
