# 🏢 AI Chief of Staff

> 企业级AI首席参谋 / 办公室主任 — 私有化部署、深度集成飞书、辅助CEO进行战略决策

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.x-orange.svg)](https://langchain-ai.github.io/langgraph/)

一个完全运行在你自己服务器上的"AI办公室主任"，通过飞书API深度集成你的工作流，帮CEO做情报分析、任务派发、风险预警和团队管理。

---

## ✨ 核心功能

| 模块 | 说明 |
|------|------|
| 📰 **情报简报** | 每日自动搜索行业新闻，AI结构化分析，自动存入知识库 |
| 📋 **智能规划** | CEO一句话指令，AI结合知识库多轮对话拆解任务，飞书审批后自动派发 |
| 📚 **知识管理** | 自动监控飞书文档变更，向量化存储，支持语义搜索（pgvector） |
| 🚨 **风险预警** | 扫描多维表格延期任务和群聊负面情绪，主动推送风险报告 |
| 👥 **人事管理** | 员工能力画像、贡献排行榜（日/周/月/年），AI自动维护指标 |

## 🎯 适合谁用

- **企业CEO** — 想要AI助理处理日常运营，但不愿数据上公网
- **高管团队** — 需要项目风险洞察和团队效能分析
- **飞书重度用户** — 已有完善的飞书工作流，想接入AI能力

## 🏗️ 技术架构

```
┌──────────────────────────────────────────┐
│    Streamlit 管理后台 (port 8501)        │
└─────────────────┬────────────────────────┘
                  │
┌─────────────────▼────────────────────────┐
│    FastAPI 后端 (port 8000)              │
│    + LangGraph 多Agent协同                │
│    + 飞书 API 集成                        │
└──┬───────────────┬────────────────┬──────┘
   │               │                │
┌──▼──────┐   ┌───▼──────┐    ┌───▼─────┐
│Postgres │   │  Redis   │    │ Celery  │
│+pgvector│   │ (缓存+   │    │ (后台   │
│         │   │  队列)    │    │  任务)  │
└─────────┘   └──────────┘    └─────────┘
```

- **多Agent编排**: LangGraph + Redis Checkpoint（支持HITL中断恢复）
- **大模型**: SiliconFlow API (DeepSeek-V3/V4-Pro)
- **向量检索**: PostgreSQL + pgvector + BGE-large-zh-v1.5
- **任务调度**: Celery + Celery Beat
- **飞书集成**: lark-oapi SDK + 自实现REST API封装

## 🚀 快速开始

> **第一次部署、不熟悉 Docker？** 直接看 [`docs/INSTALL.md`](docs/INSTALL.md) — 面向小白的一步步图文手册（约 40 分钟跑通）。
>
> 下面是给已经熟悉容器化部署的运维同学看的速通版。

### 前置要求

- Docker & Docker Compose
- 一个 [SiliconFlow](https://siliconflow.cn) API Key（注册送14元免费额度）
- （可选）飞书自建应用的 App ID / App Secret

### 一键部署

**Linux / macOS:**
```bash
git clone https://github.com/AI-For-Management/ai-chief-of-staff.git
cd ai-chief-of-staff
chmod +x install.sh
./install.sh
```

**Windows:**
```cmd
git clone https://github.com/AI-For-Management/ai-chief-of-staff.git
cd ai-chief-of-staff
install.bat
```

部署完成后访问：
- 🖥️ 管理后台: http://localhost:8501
- 📚 API文档: http://localhost:8000/docs

### 手动部署

```bash
# 1. 复制配置
cp .env.example .env

# 2. 编辑 .env 填入 SILICONFLOW_API_KEY 和 AUTH_USERS

# 3. 启动
docker compose up -d --build

# 4. 初始化数据库
docker compose exec fastapi alembic upgrade head
```

## 📖 文档

- [`docs/INSTALL.md`](docs/INSTALL.md) — **小白安装手册**（推荐第一次部署的人看这个）
- [`DEPLOY.md`](DEPLOY.md) — 简明部署指南（面向运维）
- [`docs/SECURITY.md`](docs/SECURITY.md) — 安全配置与密钥管理
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — 日常运维手册（备份/日志/故障排查）
- [`docs/MONITORING.md`](docs/MONITORING.md) — 监控速查与告警
- [`README_CEO.md`](README_CEO.md) — CEO使用说明书（面向最终用户）
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 贡献指南

## 🛠️ 项目结构

```
ai-chief-of-staff/
├── app/
│   ├── agents/              # LangGraph多Agent图
│   │   ├── briefing_graph.py
│   │   ├── task_graph.py
│   │   └── alert_graph.py
│   ├── api/                 # FastAPI路由
│   ├── services/
│   │   ├── feishu/         # 飞书API封装
│   │   ├── llm.py          # LLM调用
│   │   ├── rag.py          # 向量检索
│   │   └── news.py         # 情报抓取
│   ├── workers/            # Celery定时任务
│   └── models/             # SQLAlchemy ORM
├── streamlit_app/          # 管理后台前端
├── alembic/                # 数据库迁移
├── docker-compose.yml
└── Dockerfile
```

## 🔐 数据安全

- **本地部署**: 所有数据存储在你自己的服务器
- **登录认证**: Streamlit层支持用户名密码（在 `.env` 配置）
- **API Key隔离**: SiliconFlow Key 仅用于LLM调用，不上传任何业务数据
- **飞书凭证**: 加密存储在本地数据库

## 📦 已实现功能清单

- [x] 多Agent协同（情报/规划/预警/HR）
- [x] LangGraph + HITL审批流
- [x] 飞书Bitable / Docs / Wiki / Tasks 集成
- [x] 向量知识库（pgvector）
- [x] 多轮对话式任务拆解
- [x] 员工贡献指数与排行榜
- [x] Streamlit登录认证
- [x] Celery定时任务
- [ ] 多租户SaaS模式（规划中）
- [ ] 用户注册系统（规划中）
- [ ] 飞书云文档自动创建（规划中）

## 🤝 贡献

欢迎提交Issue和Pull Request！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📜 开源协议

[Apache License 2.0](LICENSE)

## 💬 社区

- Issues: 报告Bug或提出功能建议
- Discussions: 使用问题、最佳实践分享

---

<sub>⭐ 如果这个项目对你有帮助，请给个Star支持一下！</sub>
