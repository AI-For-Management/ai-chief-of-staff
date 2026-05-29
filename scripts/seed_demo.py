#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试场景: 星辰科技 — AI客服SaaS初创公司
造数据: 6名员工 + 2个项目 + 部分历史指标
"""
import io
import requests
from datetime import datetime, timedelta
import random
import sys

# 强制 stdout/stderr 用 UTF-8（解决 Windows 控制台中文乱码）
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

API_BASE = "http://localhost:8000"


def check_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def create_employees():
    """创建6名员工"""
    employees = [
        {"name": "张明远", "employee_id": "T001", "department": "技术部", "position": "技术总监",
         "skills": {"Python": 90, "系统架构": 92, "团队管理": 85, "Kubernetes": 80}},
        {"name": "李婧", "employee_id": "T002", "department": "技术部", "position": "高级后端工程师",
         "skills": {"Python": 88, "PostgreSQL": 85, "FastAPI": 82}},
        {"name": "王浩然", "employee_id": "T003", "department": "技术部", "position": "前端工程师",
         "skills": {"React": 85, "TypeScript": 80, "UI设计": 70}},
        {"name": "陈思琪", "employee_id": "P001", "department": "产品部", "position": "产品经理",
         "skills": {"产品规划": 88, "用户研究": 85, "Axure": 80}},
        {"name": "刘梓涵", "employee_id": "P002", "department": "产品部", "position": "产品助理",
         "skills": {"需求文档": 75, "项目协调": 70}},
        {"name": "赵晓宇", "employee_id": "S001", "department": "销售部", "position": "销售总监",
         "skills": {"客户关系": 90, "商务谈判": 88, "团队管理": 82}},
    ]

    created_ids = {}
    headers = {"Content-Type": "application/json; charset=utf-8"}
    for emp in employees:
        try:
            r = requests.post(f"{API_BASE}/api/hr/employees",
                              json=emp, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                created_ids[emp["name"]] = data["id"]
                print(f"  ✓ 员工: {emp['name']} ({emp['position']})")
            else:
                # 可能已经存在
                print(f"  ⚠ {emp['name']}: {r.status_code} - {r.text[:80]}")
        except Exception as e:
            print(f"  ✗ {emp['name']}: {e}")

    if not created_ids:
        # 拉取已有员工
        r = requests.get(f"{API_BASE}/api/hr/employees", timeout=10)
        for emp in r.json():
            created_ids[emp["name"]] = emp["id"]

    return created_ids


def create_projects(emp_ids: dict):
    """创建2个项目"""
    today = datetime.now()

    projects = [
        {
            "name": "智能客服Bot v2.0",
            "description": "升级现有客服Bot，引入大模型多轮对话能力，目标三周内上线，支撑10万+日活",
            "owner_id": emp_ids.get("张明远"),
            "status": "in_progress",
            "start_date": (today - timedelta(days=7)).isoformat(),
            "end_date": (today + timedelta(days=21)).isoformat(),
            "milestones": [
                {"date": (today - timedelta(days=3)).strftime("%Y-%m-%d"), "title": "技术方案评审", "status": "done"},
                {"date": (today + timedelta(days=10)).strftime("%Y-%m-%d"), "title": "Beta内测", "status": "pending"},
                {"date": (today + timedelta(days=21)).strftime("%Y-%m-%d"), "title": "正式上线", "status": "pending"},
            ],
            "members": [
                {"employee_id": emp_ids["张明远"], "role": "技术负责人", "responsibilities": "架构设计+代码评审"},
                {"employee_id": emp_ids["李婧"], "role": "后端开发", "responsibilities": "对话引擎+API集成"},
                {"employee_id": emp_ids["王浩然"], "role": "前端开发", "responsibilities": "客服工作台UI"},
                {"employee_id": emp_ids["陈思琪"], "role": "产品经理", "responsibilities": "需求梳理+用户测试"},
            ],
        },
        {
            "name": "客户数据看板",
            "description": "为销售团队搭建客户使用情况数据看板，支持自定义维度、实时刷新、导出报表",
            "owner_id": emp_ids.get("陈思琪"),
            "status": "planning",
            "start_date": (today + timedelta(days=14)).isoformat(),
            "end_date": (today + timedelta(days=60)).isoformat(),
            "milestones": [
                {"date": (today + timedelta(days=14)).strftime("%Y-%m-%d"), "title": "需求评审", "status": "pending"},
                {"date": (today + timedelta(days=35)).strftime("%Y-%m-%d"), "title": "原型开发完成", "status": "pending"},
            ],
            "members": [
                {"employee_id": emp_ids["陈思琪"], "role": "产品负责人", "responsibilities": "需求和原型"},
                {"employee_id": emp_ids["刘梓涵"], "role": "产品助理", "responsibilities": "用户访谈+文档"},
                {"employee_id": emp_ids["赵晓宇"], "role": "业务方", "responsibilities": "提供销售场景需求"},
            ],
        },
    ]

    project_ids = {}
    for p in projects:
        try:
            r = requests.post(f"{API_BASE}/api/projects", json=p, timeout=15)
            if r.status_code == 200:
                data = r.json()
                project_ids[p["name"]] = data["id"]
                print(f"  ✓ 项目: {p['name']}")
            else:
                print(f"  ✗ {p['name']}: {r.status_code} - {r.text[:80]}")
        except Exception as e:
            print(f"  ✗ {p['name']}: {e}")
    return project_ids


def add_timeline(project_ids: dict):
    """给"智能客服Bot"项目添加进展事件"""
    if "智能客服Bot v2.0" not in project_ids:
        return
    pid = project_ids["智能客服Bot v2.0"]
    events = [
        ("完成技术方案评审，确认采用LangGraph+流式响应", "张明远"),
        ("对话引擎核心模块开发完成，准备进入测试", "李婧"),
        ("前端工作台页面完成原型设计", "王浩然"),
        ("发现知识库召回精度不足，需要加入rerank模型", "李婧"),  # 故意埋一个风险
    ]
    for ev, author in events:
        try:
            requests.post(f"{API_BASE}/api/projects/{pid}/timeline",
                          json={"event": ev, "author": author}, timeout=10)
            print(f"  ✓ 进展: {ev[:30]}...")
        except Exception:
            pass


def create_metrics(emp_ids: dict):
    """模拟造一些月度指标数据（直接通过SQL更便捷，但用API保持一致）"""
    # 由于没有指标的写入API，这里只能让HR Agent自动跑
    # 输出提示让用户手动触发
    print("  i 提示: 请稍后通过 API: POST /api/hr/metrics/refresh 触发指标计算")


def print_summary(emp_ids: dict, project_ids: dict):
    print("\n" + "=" * 60)
    print("  数据准备完成")
    print("=" * 60)
    print(f"\n员工 ({len(emp_ids)}):")
    for name, _id in emp_ids.items():
        print(f"  • {name}  ({_id[:8]}...)")
    print(f"\n项目 ({len(project_ids)}):")
    for name, _id in project_ids.items():
        print(f"  • {name}  ({_id[:8]}...)")


def main():
    print("=" * 60)
    print("  端到端测试场景: 星辰科技 — AI客服SaaS初创公司")
    print("=" * 60)
    print()

    print("1/5  健康检查...")
    h = check_health()
    if h.get("db") != "ok" or h.get("redis") != "ok":
        print(f"  ✗ 系统未就绪: {h}")
        sys.exit(1)
    print(f"  ✓ DB: {h['db']}, Redis: {h['redis']}")

    print("\n2/5  创建员工...")
    emp_ids = create_employees()

    print("\n3/5  创建项目...")
    project_ids = create_projects(emp_ids)

    print("\n4/5  添加项目进展...")
    add_timeline(project_ids)

    print("\n5/5  指标数据...")
    create_metrics(emp_ids)

    print_summary(emp_ids, project_ids)

    print("\n下一步：阅读 SCENARIO.md 按操作手册体验完整流程\n")


if __name__ == "__main__":
    main()
