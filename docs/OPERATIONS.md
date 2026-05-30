# 运维手册 — AI 首席参谋

面向已部署系统的日常运维。安全与密钥生成见 `docs/SECURITY.md`，部署步骤见 `DEPLOY.md`。

---

## 1. 系统组成

6 个 Docker 容器（`docker compose ps` 查看）：

| 容器 | 作用 | 端口 |
|------|------|------|
| `postgres` | PostgreSQL + pgvector，主数据库 | 5432 |
| `redis` | 缓存 + Celery broker + LangGraph checkpoint | 6379 |
| `fastapi` | 后端 API（uvicorn，2 workers） | 8000 |
| `celery-worker` | 异步任务执行 | — |
| `celery-beat` | 定时任务调度 | — |
| `streamlit` | 前端 Web 界面 | 8501 |

数据持久化卷：`pgdata`（数据库）、`redisdata`（缓存）、`./backups`（数据库备份）。

---

## 2. 启停与状态

```bash
# 启动全部服务
docker compose up -d

# 查看运行状态
docker compose ps

# 重启单个服务（如改了前端代码）
docker compose restart streamlit

# 停止全部（数据保留）
docker compose down

# 停止并删除数据卷（危险：会清空数据库）
docker compose down -v
```

Windows 下也可用 `scripts/start.bat` / `stop.bat` / `restart.bat` / `status.bat`。

---

## 3. 健康检查

三档健康端点：

| 端点 | 含义 | 用途 |
|------|------|------|
| `GET /health/live` | 进程存活（始终 200） | 容器 healthcheck |
| `GET /health/ready` | 依赖就绪（DB+Redis 全好才 200，否则 503） | 负载均衡摘流 |
| `GET /health` | 整体健康（任一依赖故障 503） | 人工巡检 |

```bash
# 巡检命令（注意看 HTTP 状态码）
curl -i http://localhost:8000/health
```

依赖故障时返回示例（HTTP 503）：
```json
{"db": "ok", "redis": "Error 111 connecting to redis:6379..."}
```

---

## 4. 日志

日志为**结构化 JSON**（单行一条），便于采集。每条 API 请求带 `request_id`，可串联同一请求的多条日志。

```bash
# 实时跟踪后端日志
docker compose logs -f fastapi

# 看最近 200 行
docker compose logs --tail 200 fastapi

# 看定时任务日志
docker compose logs -f celery-beat celery-worker

# 用 jq 过滤错误级别（若装了 jq）
docker compose logs --no-log-prefix fastapi | jq 'select(.level=="ERROR")'
```

日志字段：`ts`（UTC 时间）、`level`、`logger`、`message`、`request_id`（请求内）、`method`/`path`/`status`/`duration_ms`（请求完成时）。

> 健康检查请求（`/health*`）默认不记录，仅在出错（status≥400）时记录，避免刷屏。

---

## 5. 数据库备份与恢复

### 自动备份
`celery-beat` 每天 **03:17** 执行 `backup_database` 任务：
- 用 `pg_dump` 导出，gzip 压缩到 `./backups/backup_<db>_<时间戳>.sql.gz`
- 自动保留最近 **14 份**，更早的删除（可用环境变量 `BACKUP_RETENTION` 调整）

```bash
# 查看已有备份
ls -lh backups/

# 手动立即备份一次
docker compose exec celery-worker \
  celery -A app.workers.celery_app call app.workers.backup_tasks.backup_database
```

### 恢复
```bash
# 1. 解压备份
gunzip -k backups/backup_chief_of_staff_2026-05-30_031700.sql.gz

# 2. 恢复到数据库（会覆盖现有数据，操作前先确认）
cat backups/backup_chief_of_staff_2026-05-30_031700.sql | \
  docker compose exec -T postgres psql -U chief -d chief_of_staff
```

> 恢复是破坏性操作。生产环境建议先 `docker compose down` 停服务、备份当前数据卷，再恢复。

---

## 6. 定时任务一览（Celery Beat）

时区 `Asia/Shanghai`。定义见 `app/workers/celery_app.py`。

| 任务 | 时间 | 说明 |
|------|------|------|
| 每日情报简报 | 08:00 | 生成行业情报 |
| 数据库备份 | 03:17 | 自动备份 + 清理 |
| KB 去重分类 | 03:00 | 知识库整理 |
| 文档扫描 | 每 6 小时 | 飞书文档同步 |
| 风险预警 | 09:30 / 17:30 | 项目风险扫描 |
| HR 指标更新 | 23:00 | 员工贡献指标 |
| 员工询问 | 周二/周五 09:00 | 飞书私聊催进展 |

```bash
# 确认 beat 是否在正常调度
docker compose logs --tail 50 celery-beat
```

---

## 7. 错误追踪（Sentry，可选）

`.env` 配置 `SENTRY_DSN` 后，后端和前端的未捕获异常会自动上报。留空则完全跳过、不影响运行。前端页面出错时显示友好错误页（含可展开的技术细节），不会暴露红色堆栈给用户。

---

## 8. 常见故障排查

| 现象 | 排查方向 |
|------|---------|
| 前端打不开 | `docker compose ps` 看 streamlit 是否 Up；`logs streamlit` 看报错 |
| 前端能开但数据空 | `curl -i localhost:8000/health` 看后端/DB/Redis；看 `logs fastapi` |
| `/health` 返回 503 | 看返回体里 `db`/`redis` 哪个不是 ok，重启对应容器 |
| 定时任务不跑 | `logs celery-beat`（调度）+ `logs celery-worker`（执行） |
| 飞书消息收不到 | 确认 webhook 公网地址（cloudflared）通；看 `logs fastapi` 里 webhook 请求 |
| 容器反复重启 | `docker compose ps` 看 restart 次数；`logs <容器>` 看崩溃原因；查内存是否超 `deploy.resources.limits` |
| AI 回答失败 | 确认 `.env` 的 `SILICONFLOW_API_KEY` 有效、有余额；看 `logs fastapi` |

### 资源限制
各容器在 `docker-compose.yml` 设了内存上限（postgres 2G / fastapi 2G / worker 1G / redis 512M / beat 512M / streamlit 1G）。频繁 OOM 重启时按需调高。

---

## 9. 升级与回滚

```bash
# 拉取新代码后重建镜像并重启
docker compose build
docker compose up -d

# 数据库结构变更（如有新 alembic 版本）
docker compose exec fastapi alembic upgrade head

# 回滚：切回旧代码 + 恢复对应时间点的数据库备份
```

> 升级前务必先手动备份一次数据库（见第 5 节）。
