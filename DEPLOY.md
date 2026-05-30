# AI首席参谋 — 部署指南（面向客户IT）

## 一、服务器要求

| 项目 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2核 | 4核 |
| 内存 | 4GB | 8GB |
| 硬盘 | 20GB | 50GB SSD |
| 系统 | Ubuntu 20.04+ / CentOS 8+ / Windows Server 2019+ | Ubuntu 22.04 |
| 网络 | 能访问飞书API和SiliconFlow API | 同左 |

## 二、前置安装

### Linux（推荐）
```bash
# 安装Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装Docker Compose（已内置于新版Docker）
docker compose version
```

### Windows
安装 Docker Desktop: https://www.docker.com/products/docker-desktop/

## 三、一键部署

```bash
# 1. 将项目文件传输到服务器
scp -r AI-Secretary/ user@server:/opt/

# 2. 进入目录
cd /opt/AI-Secretary

# 3. 一键部署
chmod +x install.sh
./install.sh
```

脚本会引导你输入：
- SiliconFlow API Key
- 管理员账号密码

⚠️ **生产部署额外要求**：参见 [SECURITY.md](docs/SECURITY.md) 配置 `APP_ENCRYPTION_KEY`、`ADMIN_API_TOKEN`、`ADMIN_PASSWORD_HASH`。
- CEO账号密码

## 四、手动配置（如需）

编辑 `.env` 文件：

```bash
nano .env
```

关键配置项：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `SILICONFLOW_API_KEY` | AI大模型密钥 | `sk-xxxx` |
| `AUTH_USERS` | 登录账号（用户名:密码,逗号分隔） | `admin:Pass123,ceo:Boss888` |
| `FEISHU_APP_ID` | 飞书应用ID | `cli_a5xxx` |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | `xxxxx` |

修改后重启：
```bash
docker compose up -d --force-recreate
```

## 五、访问地址

| 服务 | 地址 | 用途 |
|------|------|------|
| 管理后台 | `http://服务器IP:8501` | CEO日常使用 |
| API文档 | `http://服务器IP:8000/docs` | 技术调试 |
| API健康检查 | `http://服务器IP:8000/health` | 监控 |

## 六、域名配置（可选）

如需通过域名访问（如 `ai.company.com`），用Nginx反向代理：

```nginx
server {
    listen 80;
    server_name ai.company.com;

    # Streamlit管理后台
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    location /webhook/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

## 七、日常运维

```bash
# 查看所有服务状态
docker compose ps

# 查看日志
docker compose logs -f              # 全部日志
docker compose logs -f fastapi      # 后端日志
docker compose logs -f celery-worker # 定时任务日志

# 重启
docker compose restart

# 停止
docker compose down

# 更新（拿到新代码后）
docker compose up -d --build

# 数据库备份
docker compose exec postgres pg_dump -U chief chief_of_staff > backup_$(date +%Y%m%d).sql

# 数据库恢复
cat backup.sql | docker compose exec -T postgres psql -U chief chief_of_staff
```

## 八、防火墙

需要开放的端口：

| 端口 | 服务 | 说明 |
|------|------|------|
| 8501 | Streamlit | 管理后台（CEO访问） |
| 8000 | FastAPI | API（飞书Webhook回调需要） |

```bash
# Ubuntu
sudo ufw allow 8501
sudo ufw allow 8000

# CentOS
sudo firewall-cmd --add-port=8501/tcp --permanent
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

## 九、故障排查

| 现象 | 排查 |
|------|------|
| 管理后台打不开 | `docker compose ps` 看streamlit是否运行 |
| 登录失败 | 检查 `.env` 中 `AUTH_USERS` 格式是否正确 |
| 情报简报为空 | 检查容器网络是否能访问外网 |
| 飞书连接失败 | 检查飞书App ID/Secret是否正确，应用是否已发布 |
| 数据库连接失败 | `docker compose logs postgres` 查看数据库日志 |
