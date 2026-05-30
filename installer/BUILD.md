# 安装包构建手册（维护者用）

> 本文档面向**项目维护者**，目的是从源码生成可交付给客户的 `AI首席参谋-Setup-x.y.z.exe`。
> 客户拿到这个 .exe 后，全程双击即可，无需懂命令行。
> 客户视角的安装步骤见 [`docs/INSTALL.md`](../docs/INSTALL.md)。

---

## 一、产物形态

最终交付给客户的就是一个文件：

```
AI首席参谋-Setup-0.1.0.exe   (约 200-300 MB，含项目代码 + 启动器)
```

客户拿到后双击 → 走 Inno Setup 标准向导 → 桌面生成「AI 首席参谋」图标 → 双击运行。
首次运行时弹出图形化配置向导，让用户填 SiliconFlow API Key + 设管理员密码，自动写入 `.env` 并启动所有 Docker 服务、自动打开浏览器。

---

## 二、需要在维护者电脑装的工具

| 工具 | 版本 | 下载 |
|------|------|------|
| Go | 1.22+ | https://go.dev/dl/ |
| TDM-GCC（C 编译器，CGO 用） | 任意新版 | https://jmeubank.github.io/tdm-gcc/ |
| Inno Setup | 6.2+ | https://jrsoftware.org/isinfo.php |
| Git for Windows（含 bash） | 任意 | https://git-scm.com/download/win |

> **如果 prepare.sh 在 PowerShell 跑不了**，用 Git Bash 跑（装 Git 时会一起装上）。

环境验证：
```bash
go version              # go1.22+
gcc --version           # 显示 mingw 版本
iscc /?                 # Inno Setup 命令行（可选，也可用 GUI）
```

---

## 三、打包流程（5 步）

### Step 1 准备图标（仅首次）

把 256×256 的 `.ico` 文件放到：
```
installer/assets/icon.ico
```

> 没有的话从 PNG 转：在线工具 https://convertio.co/png-ico/ 上传 PNG → 选 256×256 → 下载。

### Step 2 编译 launcher 和 configurator

在仓库根目录（Git Bash）：

```bash
bash installer/prepare.sh
```

它会：
1. 用 Go 交叉编译出 `installer/bin/AI首席参谋.exe`（系统托盘启动器）
2. 用 Go 编译 `installer/bin/configurator.exe`（首次配置向导）
3. 把图标拷到 `installer/bin/icon.ico`
4. 把仓库本体（去掉 `.git`、`.env`、`launcher/`、`configurator/`、`installer/` 等）拷到 `installer/payload/`

成功后看到：
```
==> 准备完成
    bin/      : AI首席参谋.exe configurator.exe icon.ico
    payload/  : 84M
```

⚠️ 如果 configurator 编译报 CGO 错误：
- Windows：装好 TDM-GCC 后，在系统环境变量 PATH 里加 `C:\TDM-GCC-64\bin`
- 重启 Git Bash 让 PATH 生效

### Step 3 编译安装包

**方式 A：GUI（推荐第一次用）**

1. 打开 Inno Setup Compiler
2. File → Open → 选 `installer/setup.iss`
3. Build → Compile (F9)
4. 编译完成后看到 `installer/dist/AI首席参谋-Setup-0.1.0.exe`

**方式 B：命令行**

```bash
# Windows cmd / PowerShell
cd installer
"C:\Program Files (x86)\Inno Setup 6\iscc.exe" setup.iss
```

带版本号：

```bash
APP_VERSION=0.1.0 "C:\Program Files (x86)\Inno Setup 6\iscc.exe" setup.iss
```

### Step 4 在干净的电脑上验证

**这一步必做。** 你自己电脑里 Docker / Python / Go 都装得整整齐齐，不能代表客户环境。

最低验证流程：
1. 找一台没装过这些工具的 Windows 11（或开个全新 VM）
2. 拷 `Setup.exe` 过去双击
3. 走完安装向导
4. 双击桌面图标
5. 配置向导填 SiliconFlow Key + 密码
6. 等 1-3 分钟 → 浏览器自动开 → 能登录就算成功

如果 Docker Desktop 没装，安装器会询问是否打开下载页面。

### Step 5 发布

把 `installer/dist/AI首席参谋-Setup-0.1.0.exe` 上传到客户能拿到的地方：
- 公司私有云盘
- GitHub Releases（如果项目公开）
- 客户专属 SFTP

随附一份 [`docs/INSTALL.md`](../docs/INSTALL.md) 转成 PDF 或 Word，方便不联网阅读。

---

## 四、Setup.exe 内部都做了什么

| 阶段 | 行为 |
|------|------|
| 安装前检查 | 检测 Docker Desktop 是否装好；没装则询问引导用户先装 |
| 文件释放 | 释放 `installer/payload/*` → `C:\Program Files\AI 首席参谋\`<br>释放 `installer/bin/*` → `C:\Program Files\AI 首席参谋\bin\` |
| 快捷方式 | 桌面 + 开始菜单 → 指向 `bin\AI首席参谋.exe` |
| 注册表 | 用户勾选了"开机自启"才写入 `HKLM\Run` |
| 卸载入口 | 控制面板「添加或删除程序」可见，卸载时先 `docker compose down` |

启动器（launcher）首次运行时会：
1. 检查 `.env` 是否存在/完整
2. 不完整 → 拉起 `configurator.exe`（GUI 配置向导）
3. 配置完成 → 启动 Docker Desktop（如未运行）→ `docker compose up -d`
4. 轮询 `/health/ready` → 弹 Toast 通知 → 自动开浏览器
5. 常驻系统托盘（右键菜单：打开 / 重启 / 日志 / 停止 / 退出）

---

## 五、版本升级如何打包

每次发布新版本：

```bash
# 1. 改 VERSION 文件
echo "0.2.0" > VERSION

# 2. 打 tag 并推送
git tag v0.2.0
git push origin v0.2.0

# 3. 重跑 prepare + 编译
APP_VERSION=0.2.0 bash installer/prepare.sh
APP_VERSION=0.2.0 "C:\Program Files (x86)\Inno Setup 6\iscc.exe" installer\setup.iss
```

客户升级时：
- **方式 A（推荐）**：直接双击新 Setup.exe，会覆盖安装。`.env` 不会被动（已存在则跳过 configurator）。但 Docker 容器需要手动 `docker compose pull && docker compose up -d`。
- **方式 B**：客户自行 `git pull && bash scripts/upgrade.sh`（适用于懂命令行的客户）。

> TODO：v0.3 加入"启动器内 → 检测新版本 → 一键升级"按钮。

---

## 六、常见问题

### Q1 Setup.exe 体积太大（>500 MB）
检查 `installer/payload/` 是否误带了不该带的：
```bash
du -sh installer/payload/* | sort -h
```
重点看 `node_modules/`、`.git/`、`backups/`、`__pycache__/`。`prepare.sh` 已默认排除这些，但如果改过脚本要复查。

### Q2 客户电脑提示"无法验证发布者"
.exe 没签名导致 SmartScreen 警告。两条路：
- 短期：让客户点"更多信息" → "仍要运行"
- 长期：买代码签名证书（DigiCert / GlobalSign 起步价 ≈ ¥1500/年），在 Inno Setup 编译产物上 `signtool sign`

### Q3 Configurator 在 Win10 旧版打不开
Fyne 需要 OpenGL。Windows 10 1809 之前的版本 Mesa 软件渲染可能崩。让客户升级 Win10 或装 Mesa3D dll。

### Q4 客户企业禁用 Docker Desktop
Docker Desktop 在大公司有商用许可问题。备选：
- 引导客户装 **Rancher Desktop**（免费、API 兼容）
- 或装 **Podman Desktop** + `podman-compose`（需要小幅改造启动器命令）

---

## 七、后续可加项（投产稳定后）

- [ ] **代码签名**：消除 SmartScreen 警告
- [ ] **自动更新**：启动器内置 GitHub Releases 检查 + 一键升级
- [ ] **离线安装包**：把 Docker Desktop 的 .exe 也打进 Setup.exe（约 +500MB），客户彻底无需访问公网
- [ ] **Rancher Desktop 兼容模式**：不强依赖 Docker Desktop
- [ ] **跨平台**：mac `.dmg` / Linux `.deb`（Fyne + Inno Setup 一致替换为 fpm）
