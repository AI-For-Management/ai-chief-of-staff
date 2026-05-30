# 安全配置与运维 — AI 首席参谋

> 适用于生产/客户私有部署。开发模式可放宽，但客户交付前请按本文档全部完成。

---

## 1. 必填密钥

生产部署的 `.env` 中**这三个必填**：

| 变量 | 用途 | 生成命令 |
|------|------|---------|
| `APP_ENCRYPTION_KEY` | 加密 DB 中的飞书 secret 等敏感字段 | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `ADMIN_API_TOKEN` | `/api/admin/*` 端点的 Bearer 令牌 | `openssl rand -hex 32` |
| `ADMIN_PASSWORD_HASH` | Streamlit admin 用户的 bcrypt 哈希 | `python -c "import bcrypt; print(bcrypt.hashpw(b'YourStrongPwd', bcrypt.gensalt()).decode())"` |

可选：

| 变量 | 用途 |
|------|------|
| `SENTRY_DSN` | 错误追踪到 Sentry（留空则关闭） |
| `APP_ENV` | 设为 `production` 后启用强制安全检查 |

---

## 2. 生产部署前检查清单

```
☐ 已生成并写入 APP_ENCRYPTION_KEY
☐ 已生成并写入 ADMIN_API_TOKEN
☐ 已生成并写入 ADMIN_PASSWORD_HASH
☐ APP_ENV=production
☐ 数据库密码 POSTGRES_PASSWORD 已改为强密码（不再用默认 chief_secret_2024）
☐ .env 文件权限为 600（chmod 600 .env）
☐ 防火墙仅开放需要的端口（8501 给 CEO，8000 仅供飞书 webhook）
☐ 已设置自动备份（见下文）
☐ 已对现有 lark_configs 表做加密迁移（见下文）
```

---

## 3. 加密现有飞书凭证

如果是**升级到加密版本的旧部署**，DB 里飞书 `app_secret` 还是明文，执行：

```bash
docker compose exec fastapi python /app/scripts/encrypt_existing_secrets.py
```

输出示例：
```
✓ 已加密配置: 测试 (id=...)
迁移完成:
  checked: 1
  encrypted: 3
  skipped_already_encrypted: 0
  skipped_empty: 0
```

⚠️ **重要**：执行完后**绝不能丢失** `APP_ENCRYPTION_KEY`，否则数据无法解密。建议把它保存到密钥管理工具（1Password / Bitwarden / Vault）。

---

## 4. /admin API 鉴权

启用 `ADMIN_API_TOKEN` 后，所有 `/api/admin/*` 端点必须带 Authorization 头：

```bash
# 正确
curl -H "Authorization: Bearer <ADMIN_API_TOKEN>" http://localhost:8000/api/admin/lark-configs

# 错误（401）
curl http://localhost:8000/api/admin/lark-configs
# {"detail":"缺少 Authorization: Bearer <token> 头"}
```

Streamlit 端会从 .env 自动读取并附加该 token。

---

## 5. 自动数据库备份

Celery Beat 每天凌晨 3:17 自动备份到 `./backups/chief-YYYYMMDD.sql.gz`，保留最近 14 份。

手动触发：
```bash
docker compose exec celery-worker python -c "from app.workers.backup_tasks import backup_database; print(backup_database())"
```

恢复某次备份：
```bash
zcat backups/chief-20260601.sql.gz | docker compose exec -T postgres psql -U chief chief_of_staff
```

---

## 6. 健康检查

```bash
curl -i http://localhost:8000/health        # 整体（任一依赖故障 503）
curl -i http://localhost:8000/health/live   # 进程是否在跑（始终 200，进程死了连不上）
curl -i http://localhost:8000/health/ready  # 是否可承接流量（依赖全部就绪 200）
```

监控建议挂 `/health` 端点；Kubernetes/容器编排用 `/health/live` 做 liveness、`/health/ready` 做 readiness。

---

## 7. 日志与排障

```bash
# 查全部
docker compose logs --tail 100 -f

# 查具体服务
docker compose logs fastapi --tail 100 -f
docker compose logs celery-worker --tail 100 -f

# 容器是否健康
docker compose ps
```

---

## 8. 常见安全建议

- **每月轮换** `ADMIN_API_TOKEN` 和 `ADMIN_PASSWORD_HASH`
- 飞书 `app_secret` 也建议每季度在飞书开放平台 reset 一次
- 不要把 `.env` 提交到 git（已加入 `.gitignore`）
- 客户机器上**关闭** 5432（PostgreSQL）和 6379（Redis）的对外暴露（只走容器内部网络）
- 如果客户要远程访问 8501（Streamlit），强烈建议套一层 Nginx + Basic Auth + HTTPS
