# 一键工具集

> 双击运行即可，开发者快捷操作

## Windows

| 文件 | 用途 |
|------|------|
| `start.bat` | 启动所有服务 + 自动开浏览器 |
| `stop.bat` | 停止所有服务 |
| `restart.bat` | 重启服务 |
| `logs.bat` | 实时查看日志 |
| `status.bat` | 查看容器状态和资源占用 |
| `start-silent.bat` | 静默启动（用于自启动） |
| `register-autostart.bat` | 注册开机自启（需管理员） |
| `unregister-autostart.bat` | 取消开机自启（需管理员） |
| `create-shortcuts.bat` | 在桌面创建启动/停止快捷方式 |

## Linux / macOS

| 文件 | 用途 |
|------|------|
| `start.sh` | 启动所有服务 |
| `stop.sh` | 停止所有服务 |
| `restart.sh` | 重启服务 |
| `logs.sh` | 实时查看日志 |
| `status.sh` | 查看容器状态 |

首次使用需要授权：
```bash
chmod +x scripts/*.sh
```

## 推荐使用方式

### 日常开发
直接双击根目录的 `start.bat` / `stop.bat`

### 设置开机自启（Windows）
1. 右键 `scripts\register-autostart.bat` → 以管理员身份运行
2. 重启电脑后会自动启动（登录后延迟2分钟，等Docker Desktop就绪）

### 桌面图标
双击 `scripts\create-shortcuts.bat` 在桌面生成"启动"和"停止"图标

## 故障排查

### 启动失败
1. 检查 Docker Desktop 是否运行
2. 检查 `.env` 文件是否存在且填了 `SILICONFLOW_API_KEY`
3. 查看日志：双击 `logs.bat`

### 自启动没生效
查看日志：`scripts\autostart.log`
