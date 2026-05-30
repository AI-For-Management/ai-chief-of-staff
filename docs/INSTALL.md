# AI 首席参谋 — 完整安装手册（小白版）

> **这份文档是给完全没接触过 Docker / 命令行的人写的。**
> 全程照抄命令、对照预期输出，不需要懂背后原理。
>
> 你需要准备：一台电脑、一根能上网的网线（或 Wi-Fi）、一个能收验证邮件的邮箱。
> 全程大约 **40 分钟**（其中 20 分钟在等机器自己装东西）。

---

## 目录

- [第 0 步：要装在什么样的电脑上？](#第-0-步要装在什么样的电脑上)
- [第 1 步：安装 Docker（电脑只装一次）](#第-1-步安装-docker电脑只装一次)
- [第 2 步：拿到项目代码](#第-2-步拿到项目代码)
- [第 3 步：申请一个 AI 大模型 API Key](#第-3-步申请一个-ai-大模型-api-key)
- [第 4 步：生成三把"密钥"](#第-4-步生成三把密钥)
- [第 5 步：填写 .env 配置文件](#第-5-步填写-env-配置文件)
- [第 6 步：一键启动](#第-6-步一键启动)
- [第 7 步：第一次登录](#第-7-步第一次登录)
- [第 8 步（可选）：连接飞书](#第-8-步可选连接飞书)
- [第 9 步：日常用法速查](#第-9-步日常用法速查)
- [附录 A：常见错误与解决](#附录-a常见错误与解决)
- [附录 B：迁移到另一台电脑](#附录-b迁移到另一台电脑)
- [附录 C：把它彻底删掉](#附录-c把它彻底删掉)

---

## 第 0 步：要装在什么样的电脑上？

### 硬件最低要求

| 项目 | 最低 | 推荐 |
|------|-----|-----|
| 内存 | 8 GB | 16 GB |
| 硬盘剩余空间 | 30 GB | 50 GB |
| CPU | 2 核 | 4 核 |

> 内存少于 8 GB 也能装，但跑起来会卡。

### 操作系统

支持以下三选一：
- **Windows 10/11**（家庭版以上都行）
- **macOS** 13 以上
- **Ubuntu 20.04 / 22.04** 或 CentOS 8

> 本手册以 **Windows 11** 为主。Mac 和 Linux 用户在差异处会单独标注 **`Mac/Linux:`**。

### 网络要求

电脑要能正常打开这两个网址（浏览器试一下）：
- https://www.docker.com
- https://siliconflow.cn

如果第二个打不开，看 [附录 A](#附录-a常见错误与解决) 处理。

---

## 第 1 步：安装 Docker（电脑只装一次）

> Docker 是一个能在你电脑上"装个小电脑"的工具。我们把整个 AI 系统装进这个"小电脑"，跟你日常用的 Windows 互不干扰。

### Windows / Mac 用户

1. 打开浏览器，访问 https://www.docker.com/products/docker-desktop/
2. 点蓝色按钮 **"Download Docker Desktop"** → 选你的系统
3. 下载下来的安装包**双击运行**，一路点 **"Next"** / **"Continue"** / **"Install"** 即可
4. 安装完成后**重启电脑**（很重要，不重启可能跑不起来）
5. 重启后，从开始菜单找到 **"Docker Desktop"** 双击打开
6. 第一次会让你接受协议、可能让你登录 Docker 账号——**直接选 "Skip"（跳过）即可**
7. 等 Docker 图标（鲸鱼）从橙色变为白色（在屏幕右下角任务栏），就说明 Docker 启动成功

**验证 Docker 装好了**：
按 **Win 键 + R**，输入 `cmd`，回车，弹出黑色窗口。在里面输入：
```
docker --version
```
按回车。如果看到这样一行（版本号可能不同）就说明成功：
```
Docker version 27.2.0, build 3ab4256
```

### Linux 用户（Ubuntu）

打开终端，依次粘贴执行：
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```
然后**注销并重新登录**（或者重启），再运行 `docker --version` 验证。

---

## 第 2 步：拿到项目代码

你有两种方式拿到代码。**推荐方式一**。

### 方式一：直接下载 ZIP（最简单）

1. 浏览器打开：https://github.com/AI-For-Management/ai-chief-of-staff
2. 点页面右上角绿色按钮 **"Code"** → 弹出菜单 → 点 **"Download ZIP"**
3. 下载后解压。**解压到一个简单的路径**，例如：
   - **Windows**：`D:\AI-Secretary`（不要放桌面、不要放含中文/空格的目录）
   - **Mac/Linux**：`~/AI-Secretary`

### 方式二：用 git 克隆（懂一点命令行的）

```bash
# Windows: 在 D 盘根目录右键打开 PowerShell
# Mac/Linux: 打开终端
cd D:\
git clone https://github.com/AI-For-Management/ai-chief-of-staff.git AI-Secretary
```

### 验证

进入项目目录，应该能看到这些文件：
```
D:\AI-Secretary\
├── docker-compose.yml
├── .env.example
├── DEPLOY.md
├── README.md
├── app\
├── streamlit_app\
├── docs\
└── scripts\
```

---

## 第 3 步：申请一个 AI 大模型 API Key

> 这一步是为了让系统能"思考"。我们用国内的 **SiliconFlow（硅基流动）**，注册免费、有赠送额度，能跑很久。

1. 浏览器打开：https://siliconflow.cn
2. 点右上角 **"登录/注册"**
3. 用手机号注册（微信/支付宝快捷登录也行）
4. 注册完后，点左边菜单 **"API 密钥"**
5. 点 **"新建 API 密钥"** → 起个名字（如 "ai-secretary"）→ 点 **"新建"**
6. 弹出来一个长字符串，**`sk-xxxx...`** 这样开头的，**立刻复制保存到记事本**（关掉就再也看不到了）

**记下这个 key**，下一步要用。形如：
```
sk-abc123def456ghi789...
```

> 充值额度建议：先充 50 元，能用很久。前期可能用赠送额度就够。

---

## 第 4 步：生成三把"密钥"

> 系统需要三把内部用的"钥匙"来保护数据。你不用懂它们是干嘛的，按下面的命令生成出来、复制到记事本就行。

### Windows 用户

打开 PowerShell（Win + X → 选 "Windows Terminal" 或 "PowerShell"），**逐条**粘贴执行：

```powershell
# 切换到项目目录
cd D:\AI-Secretary

# 用 Docker 里的 Python 生成（你电脑没装 Python 也能用）
docker run --rm python:3.11-slim python -c "from cryptography.fernet import Fernet; import bcrypt, os; print('APP_ENCRYPTION_KEY=' + Fernet.generate_key().decode()); print('ADMIN_API_TOKEN=' + os.urandom(32).hex())"
```

> 第一次跑会下镜像，等 1-2 分钟。第二条命令开始就快了。

```powershell
# 设置一个登录密码（自己想一个，至少 12 位、带大小写和数字），把下面 YourStrongPwd_2026 改成你自己的
docker run --rm python:3.11-slim sh -c "pip install -q bcrypt && python -c \"import bcrypt; print('ADMIN_PASSWORD_HASH=' + bcrypt.hashpw(b'YourStrongPwd_2026', bcrypt.gensalt()).decode())\""
```

⚠️ **把 `YourStrongPwd_2026` 改成你自己想的密码**。这就是你以后登录系统的密码——记好。

### Mac/Linux 用户

```bash
cd ~/AI-Secretary

# 三把钥匙
pip3 install cryptography bcrypt 2>/dev/null
python3 -c "from cryptography.fernet import Fernet; print('APP_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python3 -c "import os; print('ADMIN_API_TOKEN=' + os.urandom(32).hex())"
# 把下面的 YourStrongPwd_2026 改成你自己想的密码
python3 -c "import bcrypt; print('ADMIN_PASSWORD_HASH=' + bcrypt.hashpw(b'YourStrongPwd_2026', bcrypt.gensalt()).decode())"
```

### 你应该得到的东西

把每条命令的输出复制到记事本，应该长这样（你的内容会不同，**这是示例**）：

```
APP_ENCRYPTION_KEY=R4vN8xKj2mP9qL5sT6wU3yZ1aB7cE0dF4gH8iJ2kM6n=
ADMIN_API_TOKEN=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234
ADMIN_PASSWORD_HASH=$2b$12$X9p3mK8nQ2rT5sV4uY7wZeA1bC0dE6fG3hJ.kL9mN8oP1qR2sT4uV
```

⚠️ **绝对不能丢失 `APP_ENCRYPTION_KEY`**！它一旦丢失，加密的飞书配置就永远解不开了。建议用密码管理工具（1Password / Bitwarden / 微信收藏）保存一份。

---

## 第 5 步：填写 .env 配置文件

> `.env` 是配置文件。系统启动时会读它，知道用哪个数据库、用谁的 API key。

### 创建 .env 文件

**Windows**：
按 **Win + R**，输入 `cmd`，回车。然后：
```cmd
cd /d D:\AI-Secretary
copy .env.example .env
notepad .env
```

**Mac/Linux**：
```bash
cd ~/AI-Secretary
cp .env.example .env
# 用任何文本编辑器打开它
nano .env    # 或 vim .env / code .env
```

### 改 6 个地方

`.env` 打开后是一堆 `键=值` 的行。**只需要改这 6 处**：

#### 1. 数据库密码（建议改但不强制）

```ini
POSTGRES_PASSWORD=chief_secret_2024     ← 改成你自己想的密码（如 ChiefDB2026!@#）
DATABASE_URL=postgresql+asyncpg://chief:chief_secret_2024@postgres:5432/chief_of_staff
DATABASE_URL_SYNC=postgresql://chief:chief_secret_2024@postgres:5432/chief_of_staff
```

⚠️ **如果改了 `POSTGRES_PASSWORD`，下面两行 URL 里的 `chief_secret_2024` 也要改成同一个密码**，**3 处必须一致**。

> 没改也能用，只是数据库密码弱一些。第一次部署可以**先跳过**，等熟练后再改。

#### 2. AI API Key（必填）

```ini
SILICONFLOW_API_KEY=sk-your-key-here    ← 改成第 3 步得到的 key
```

变成：
```ini
SILICONFLOW_API_KEY=sk-abc123def456ghi789...
```

#### 3-5. 三把内部密钥（必填）

把第 4 步记事本里的三行，对应填进去：

```ini
APP_ENCRYPTION_KEY=                     ← 粘贴 APP_ENCRYPTION_KEY 那一行的值
ADMIN_API_TOKEN=                        ← 粘贴 ADMIN_API_TOKEN 那一行的值
ADMIN_PASSWORD_HASH=                    ← 粘贴 ADMIN_PASSWORD_HASH 那一行的值
```

填完后变成：
```ini
APP_ENCRYPTION_KEY=R4vN8xKj2mP9qL5sT6wU3yZ1aB7cE0dF4gH8iJ2kM6n=
ADMIN_API_TOKEN=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234
ADMIN_PASSWORD_HASH=$2b$12$X9p3mK8nQ2rT5sV4uY7wZeA1bC0dE6fG3hJ.kL9mN8oP1qR2sT4uV
```

⚠️ `=` 两边**不要有空格**。`$` 和单引号要原样保留。

#### 6. 应用环境（必填）

```ini
APP_ENV=development     ← 改成 production
```

变成：
```ini
APP_ENV=production
```

### 不要碰的字段

下面这些**保持默认即可**，新手不用改：
- `REDIS_URL`、`SILICONFLOW_BASE_URL`、`LLM_MODEL_*`、`EMBEDDING_MODEL`
- `FEISHU_*`（除非你这就要连飞书，否则后面再说）
- `AUTH_USERS`（旧版兼容字段，新部署用不上）
- `SENTRY_DSN`（监控可选）
- `LOG_LEVEL`

### 保存并关闭文件

- **Windows 记事本**：Ctrl+S → 关闭
- **Mac/Linux nano**：Ctrl+O → 回车 → Ctrl+X

---

## 第 6 步：一键启动

打开 PowerShell / 终端，进入项目目录：

```bash
# Windows
cd /d D:\AI-Secretary

# Mac/Linux
cd ~/AI-Secretary
```

执行启动命令：

```bash
docker compose up -d --build
```

> `--build` 表示"构建镜像"，第一次必须加。后续重启不用。

**第一次启动需要 5-15 分钟**（取决于网速），屏幕会刷一堆英文，是正常的。看到类似下面这样就说明启动了：

```
 ✔ Container ai-secretary-postgres-1         Healthy
 ✔ Container ai-secretary-redis-1            Healthy
 ✔ Container ai-secretary-fastapi-1          Healthy
 ✔ Container ai-secretary-celery-worker-1    Started
 ✔ Container ai-secretary-celery-beat-1      Started
 ✔ Container ai-secretary-streamlit-1        Started
```

### 验证：看 6 个容器都在跑

```bash
docker compose ps
```

应该看到 6 行，**STATUS 列都是 `Up` 或 `running`**：

```
NAME                            STATUS                    PORTS
ai-secretary-celery-beat-1      Up 30 seconds
ai-secretary-celery-worker-1    Up 30 seconds
ai-secretary-fastapi-1          Up 30 seconds (healthy)   0.0.0.0:8000->8000/tcp
ai-secretary-postgres-1         Up 35 seconds (healthy)   0.0.0.0:5432->5432/tcp
ai-secretary-redis-1            Up 35 seconds (healthy)   0.0.0.0:6379->6379/tcp
ai-secretary-streamlit-1        Up 30 seconds             0.0.0.0:8501->8501/tcp
```

如果有的容器是 `Restarting` 或 `Exited`，看 [附录 A](#附录-a常见错误与解决)。

### 验证：跑健康检查

```bash
curl http://localhost:8000/health/ready
```

应该返回：
```json
{"ready":true,"checks":{"db":"ok","redis":"ok"}}
```

### 验证：跑版本检查

```bash
curl http://localhost:8000/version
```

应该返回类似：
```json
{"version":"0.1.0","git_sha":"unknown","started_at":"2026-...","env":"production"}
```

---

## 第 7 步：第一次登录

打开浏览器，访问：

```
http://localhost:8501
```

应该看到一个深色登录页（带 AI Logo）：

- **用户名**：`admin`
- **密码**：你在第 4 步生成 `ADMIN_PASSWORD_HASH` 时**自己设的那个明文密码**（不是哈希值）

> 例如示例里的 `YourStrongPwd_2026`——填的是这个，不是 `$2b$12$...`。

登录成功 → 看到"综合面板"页面，左侧有 7 个菜单。

🎉 **到这里部署就成功了！**

---

## 第 8 步（可选）：连接飞书

> 如果你不需要飞书集成，**跳过本步**也能用 80% 的功能（AI 问答、知识库、项目管理、人事管理都能跑）。
>
> 飞书集成要做：CEO 在飞书里给 AI 发消息、AI 自动派发飞书任务、AI 写飞书 Bitable。

### 8.1 创建飞书企业自建应用

1. 浏览器打开 https://open.feishu.cn
2. 用飞书账号登录 → 进入 **"开发者后台"**
3. 点 **"创建企业自建应用"** → 起名（如 "AI 首席参谋"）→ 上传图标 → 创建
4. 创建完后，记下 **App ID** 和 **App Secret**（在"凭证与基础信息"页）

### 8.2 申请权限

在应用管理页 → **"权限管理"** → 添加以下权限：
- `im:message:send_as_bot`（发消息）
- `im:message`（收消息）
- `task:task`（管理任务）
- `bitable:app`（操作多维表格）
- `contact:user.id:readonly`（读员工 ID）

### 8.3 配置事件订阅 — 让飞书能把消息推给你

> 这一步需要让飞书的服务器能"找到"你电脑。如果你电脑在公司内网（没公网 IP），用 **Cloudflare Tunnel**（免费）打洞。

#### 装 Cloudflare Tunnel

**Windows**：
```powershell
# 下载 cloudflared
curl -L -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe

# 测试一下
.\cloudflared.exe --version
```

**Mac/Linux**：
```bash
# Mac
brew install cloudflared

# Linux
curl -L --output cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/
```

#### 跑临时 Tunnel（30 秒）

```bash
cloudflared tunnel --url http://localhost:8000
```

会输出一个公网网址，类似：
```
https://abc-def-ghi-jkl.trycloudflare.com
```

**复制这个网址**。注意：这个临时网址电脑重启后会变。如果要长期使用，注册个域名走 [Cloudflare 官方文档](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) 配持久 tunnel。

#### 在飞书后台配 Webhook

回到 https://open.feishu.cn → 你的应用 → **"事件订阅"**

- **事件订阅 URL**：`<刚才那个网址>/webhook/feishu`，例如：
  ```
  https://abc-def-ghi-jkl.trycloudflare.com/webhook/feishu
  ```
- 点 **"保存"**，飞书会发一个验证请求过来，看到"验证成功"就 OK
- 添加事件订阅：
  - `im.message.receive_v1`（接收消息）

### 8.4 在系统里录入飞书凭证

回到浏览器 `http://localhost:8501`，左侧菜单点 **"飞书配置"**：

- **App ID**：粘贴第 8.1 步的 App ID
- **App Secret**：粘贴第 8.1 步的 App Secret
- **Encrypt Key**（可选）：飞书后台"事件订阅"页面给的
- **Verification Token**（可选）：同上

点 **"保存"**。

### 8.5 测试

在飞书里给应用发一条私聊消息：
```
你好
```
应该几秒内收到 AI 回复。

---

## 第 9 步：日常用法速查

### 启动 / 停止

```bash
# 启动（每次电脑开机后）
cd D:\AI-Secretary
docker compose up -d

# 停止
docker compose down

# 重启（比如改了配置）
docker compose restart
```

### 查日志（系统出问题时）

```bash
# 看后端日志
docker compose logs fastapi --tail 100

# 实时跟踪（看完按 Ctrl+C 退出）
docker compose logs -f fastapi
```

### 备份数据库

```bash
# 立即备份一次
bash scripts/backup_now.sh

# 备份文件在 ./backups/ 目录下
ls backups/
```

> 系统每天凌晨 3:17 会自动备份，保留最近 14 天。

### 升级到新版本

```bash
git pull            # 拉新代码
bash scripts/upgrade.sh    # 自动备份 + 重建 + 重启
```

---

## 附录 A：常见错误与解决

### A1. `docker compose up` 卡在 "downloading" 不动

**原因**：网络问题，下不到 Docker 镜像。

**解决**：
1. 确认能正常打开 https://www.docker.com
2. 如果在公司内网，可能需要配代理。打开 Docker Desktop → Settings → Resources → Proxies → 填公司代理
3. 或者切到 Docker 镜像加速：Docker Desktop → Settings → Docker Engine，加上：
   ```json
   {
     "registry-mirrors": [
       "https://docker.m.daocloud.io",
       "https://dockerproxy.com"
     ]
   }
   ```
   保存 → "Apply & Restart"

### A2. `docker compose ps` 看到某个容器一直在 `Restarting`

**做法**：看那个容器的日志：
```bash
docker compose logs <容器名> --tail 50
```

例如 `docker compose logs fastapi --tail 50`。

#### 常见错误信号：

**`pydantic.ValidationError: SILICONFLOW_API_KEY field required`**
→ `.env` 里的 API key 没填或格式错。回去检查第 5 步。

**`Invalid Fernet key`**
→ `APP_ENCRYPTION_KEY` 格式不对。回去重新生成（第 4 步）。

**`bcrypt.exceptions.InvalidHashError`**
→ `ADMIN_PASSWORD_HASH` 没复制完整或有空格。重新生成。

**`could not connect to server: Connection refused`**（postgres 报）
→ `POSTGRES_PASSWORD` 在三个地方不一致。检查 `.env`。

### A3. 浏览器打开 8501 显示"无法访问"

```bash
# 确认 streamlit 容器在跑
docker compose ps streamlit

# 看它的日志
docker compose logs streamlit --tail 30
```

如果容器在跑但浏览器进不去：
- Windows 防火墙拦了 → 控制面板 → Windows Defender 防火墙 → 允许 8501 端口
- 你访问的是远程机器 → 用 `http://<那台电脑的IP>:8501`

### A4. 登录页面点登录无反应

打开浏览器开发者工具（F12）→ Console 标签 → 看红色错误。

通常是 `ADMIN_PASSWORD_HASH` 出问题：
- 哈希值里如果有 `$`，记事本里编辑时**整行不要被引号包起来**
- 整行只写 `ADMIN_PASSWORD_HASH=$2b$12$XXXX...`，没有引号

### A5. AI 不回答问题 / 一直转圈

```bash
docker compose logs fastapi --tail 50 | grep -i error
```

通常是：
- API key 没充值或额度用完 → 去 SiliconFlow 看余额
- 网络访问不到 SiliconFlow → 在电脑上 `curl https://api.siliconflow.cn` 试试

### A6. 飞书发消息没回复

```bash
docker compose logs fastapi --tail 50 | grep webhook
```

应该能看到 `飞书事件 ...` 的日志。如果完全没有，说明飞书的请求没到你的电脑：
- Cloudflare Tunnel 是不是关掉了？重新跑 `cloudflared tunnel --url http://localhost:8000`
- 飞书后台的"事件订阅 URL"是不是还指向旧的 trycloudflare 网址？（临时 tunnel 重启会变）

---

## 附录 B：迁移到另一台电脑

把整套系统从 A 电脑搬到 B 电脑。

### 在 A 电脑上

```bash
cd D:\AI-Secretary

# 1. 备份数据库
bash scripts/backup_now.sh
# 会在 backups/ 下生成一个 .sql.gz 文件

# 2. 打包必备文件
# 把以下三样都拷到 U 盘 / 网盘：
#   - 整个项目目录（含代码）
#   - .env 文件（保密！里面有密钥）
#   - backups/ 里最新那个 .sql.gz
```

⚠️ 如果你在 A 电脑上录入过飞书配置，**`APP_ENCRYPTION_KEY` 必须和 A 电脑一致**——这个 key 在 `.env` 里，所以只要 `.env` 文件原样拷过去就行。**绝对不要重新生成这个 key**。

### 在 B 电脑上

1. 完成本手册的第 1 步（装 Docker）
2. 把项目目录拷过去
3. 把 `.env` 拷到项目根目录（覆盖 .env.example 旁边）
4. 把 .sql.gz 文件放到项目目录的 `backups/` 子目录
5. 启动并恢复：
   ```bash
   cd D:\AI-Secretary
   docker compose up -d postgres redis      # 先起数据库
   bash scripts/restore.sh backups/backup_chief_of_staff_xxxxxx.sql.gz
   docker compose up -d                     # 起其余服务
   ```
6. 验证：浏览器打开 `http://localhost:8501`，员工列表/项目应当与 A 电脑一致

---

## 附录 C：把它彻底删掉

```bash
cd D:\AI-Secretary

# 温和卸载（保留数据库内容、备份文件）
bash scripts/uninstall.sh

# 彻底卸载（连数据卷一起删，不可恢复！）
bash scripts/uninstall.sh --purge
```

完成后还想清干净：
- 删除 `D:\AI-Secretary` 整个目录
- 在 Docker Desktop 里点 "Quit Docker Desktop"，然后到"添加或删除程序"卸载 Docker

---

## 还有问题？

1. 找到这一行的报错：`docker compose logs fastapi --tail 100`
2. 把这一行（包括前后 5 行）截图
3. 联系交付方提供的支持联系方式

> 提供日志比仅仅说"装不上"更容易快速诊断。

---

**祝部署顺利。** 系统跑起来后，可以从控制台 → 知识库导入公司文档 → 在「智能规划」里给 CEO 第一条指令。
