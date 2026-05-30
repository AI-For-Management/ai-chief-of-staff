"""Celery应用实例 + Beat调度配置"""
import os
from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "chief_of_staff",
    broker=redis_url,
    backend=redis_url,
    # 显式列出所有包含 @celery_app.task 的模块
    include=[
        "app.workers.intel_tasks",
        "app.workers.knowledge_tasks",
        "app.workers.alert_tasks",
        "app.workers.hr_tasks",
        "app.workers.kb_tasks",
        "app.workers.inquiry_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    worker_hijack_root_logger=False,
)

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # Phase 3: 每日情报简报 (每天8:00)
    "daily-briefing": {
        "task": "app.workers.intel_tasks.generate_daily_briefing",
        "schedule": crontab(hour=8, minute=0),
    },
    # Phase 4: 文档扫描 (每6小时)
    "doc-scan": {
        "task": "app.workers.knowledge_tasks.scan_documents",
        "schedule": crontab(hour="*/6", minute=0),
    },
    # Phase 6: 风险预警 (每天9:30和17:30)
    "risk-alert": {
        "task": "app.workers.alert_tasks.scan_risks",
        "schedule": crontab(hour="9,17", minute=30),
    },
    # HR: 每日23:00更新员工指标
    "hr-metrics": {
        "task": "app.workers.hr_tasks.update_employee_metrics",
        "schedule": crontab(hour=23, minute=0),
    },
    # KB管理员: 每天凌晨3:00 去重和分类
    "kb-manage": {
        "task": "app.workers.kb_tasks.run_kb_manage",
        "schedule": crontab(hour=3, minute=0),
    },
    # 员工询问: 周二/周五早9:00 飞书私聊问员工进展
    "employee-inquiry": {
        "task": "app.workers.inquiry_tasks.run_employee_inquiry",
        "schedule": crontab(day_of_week="tue,fri", hour=9, minute=0),
    },
}
