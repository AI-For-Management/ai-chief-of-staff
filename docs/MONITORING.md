# 监控速查 — AI 首席参谋

面向已部署系统的快速观测与告警。详细运维步骤见 `OPERATIONS.md`。

---

## 1. 关键端点

| 端点 | 用途 | 期望响应 |
|------|------|---------|
| `GET /health` | 整体健康（DB+Redis 全好才 200） | 200 + `{db:"ok",redis:"ok"}` |
| `GET /health/live` | 进程存活 | 始终 200，超时即视为挂掉 |
| `GET /health/ready` | 是否可承接流量 | 200 + `{ready:true}` |
| `GET /version` | 部署版本身份 | 200 + `{version, git_sha, started_at, env}` |

```bash
# 一键巡检（产线机器跑这个）
curl -fsS http://localhost:8000/health/ready && \
curl -fsS http://localhost:8000/version
```

---

## 2. 关键指标速览

JSON 日志中可直接 grep / jq 提取：

| 指标 | 含义 | 告警阈值 |
|------|------|---------|
| `level=ERROR` 出现频率 | 后端异常 | 5 分钟内 ≥ 5 次 → 告警 |
| `path=/webhook/feishu` 的 `status` | 飞书事件成功率 | 5 分钟内 4xx/5xx 比例 > 5% |
| `duration_ms` (path=/api/agents/*) | AI 响应耗时 | 单次 > 60s 关注；P95 > 30s 调查 |
| `path=/api/admin/*` `status=401` | /admin 鉴权拒绝 | 短时间大量 401 → 怀疑暴力破解 |
| 容器重启次数 (`docker compose ps`) | 进程稳定性 | > 3 次/天 → 看 logs 找原因 |
| 备份文件落地 | DB 备份是否正常 | `./backups/` 第二天没新文件 → 告警 |

```bash
# 5 分钟错误日志条数
docker compose logs --since 5m fastapi | grep -c '"level":"ERROR"'

# 最慢的 10 个请求
docker compose logs --no-log-prefix --since 1h fastapi | \
  jq -c 'select(.duration_ms != null)' | \
  jq -s 'sort_by(-.duration_ms) | .[0:10]'
```

---

## 3. 速率限制

`/webhook/feishu`：单 IP **120 次/分钟**（`slowapi`）。
- 触发后返回 **429 Too Many Requests**
- 飞书会自动重试，正常吞吐远低于此阈值
- 若日志频繁出现 429，说明事件风暴或被攻击，提高阈值前先排查来源

---

## 4. Sentry 错误追踪（可选）

在 `.env` 配置 `SENTRY_DSN`：
```
SENTRY_DSN=https://<key>@<org>.ingest.sentry.io/<project>
```

后端（FastAPI）和前端（Streamlit）的未捕获异常都会自动上报，包含：
- 异常堆栈
- 请求路径 / 方法
- `request_id`（与日志关联）
- `environment`（development / staging / production）

`traces_sample_rate` 默认后端 0.1（10% 采样性能 trace）、前端 0.0（仅错误）。
DSN 留空则完全跳过、零开销。

---

## 5. 推荐告警规则

针对独立部署场景（单机 Docker），最小化告警：

1. **Live 探活失败**：每分钟从外部 curl `/health/live`，连续 3 次失败 → 邮件/Slack 通知
2. **Ready 持续 503**：连续 5 分钟 ready=false → 通知（依赖故障）
3. **每日备份缺失**：每天 04:00 检查 `./backups/` 是否有当天文件 → 通知
4. **Sentry 新错误**：Sentry 自带的 issue 通知

不需要复杂的 Prometheus + Grafana 栈。客户现场用 cron + 简单 shell 即可：

```bash
# /etc/cron.d/ai-secretary-watchdog（示意）
* * * * * root curl -fsS -m 5 http://localhost:8000/health/live > /dev/null \
    || echo "[$(date)] AI-Secretary live check failed" | mail -s "ALERT" admin@example.com
```

---

## 6. 性能基线（参考值）

| 操作 | 典型耗时 |
|------|---------|
| `/health/*` | < 50ms |
| `/api/hr/*` 列表 | 50-200ms |
| `/api/agents/rag/answer`（快模型） | 5-15s |
| `/api/agents/rag/answer`（深度思考） | 30-90s |
| `/api/agents/tasks/decompose` | 20-60s |
| 风险扫描完整流程 | 30-60s |
| 数据库备份（数十 MB） | < 10s |

超出 2-3 倍基线时检查：
- LLM API（SiliconFlow）是否拥堵 / 余额
- DB 连接是否打满（`pg_stat_activity`）
- 容器内存是否接近 `deploy.resources.limits`

---

## 7. 故障定位流程

```
  请求失败/缓慢
        │
        ▼
  /health/ready 200？ ── 否 → 看 ready.checks 哪项失败 → 重启对应容器
        │ 是
        ▼
  fastapi logs 有 ERROR？── 是 → 抓 request_id 串日志定位
        │ 否
        ▼
  慢请求？看 duration_ms ─ 是 → LLM/DB 哪一步慢 → 查上游
        │ 否
        ▼
  前端报错？看 streamlit logs / Sentry
```
