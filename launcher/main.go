// AI 首席参谋 启动器
//
// 职责：
//  1. 拉起 Docker Desktop（若未运行）
//  2. 在项目目录跑 `docker compose up -d`
//  3. 轮询 /health/ready 直到就绪
//  4. 自动打开浏览器到 http://localhost:8501
//  5. 常驻系统托盘，右键菜单：打开 / 重启 / 查看日志 / 停止 / 退出
//
// 编译（Windows）:
//
//	cd launcher
//	go build -ldflags "-H=windowsgui -s -w" -o ../installer/AI首席参谋.exe
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"fyne.io/systray"
	"github.com/skratchdot/open-golang/open"
)

const (
	uiURL       = "http://localhost:8501"
	healthURL   = "http://localhost:8000/health/ready"
	startupWait = 180 * time.Second
)

// projectDir 返回项目根目录（docker-compose.yml 所在）。
// 安装后由 Inno Setup 把整个项目释放到 %ProgramData%\AI-Secretary。
// 也支持开发模式：launcher.exe 跑在仓库 launcher/ 下时回到上级。
func projectDir() string {
	exe, err := os.Executable()
	if err != nil {
		return "."
	}
	dir := filepath.Dir(exe)
	// 优先：exe 同目录里就有 docker-compose.yml
	if fileExists(filepath.Join(dir, "docker-compose.yml")) {
		return dir
	}
	// 其次：上一级（开发模式 launcher/AI首席参谋.exe → ..）
	parent := filepath.Dir(dir)
	if fileExists(filepath.Join(parent, "docker-compose.yml")) {
		return parent
	}
	// 兜底：%ProgramData%\AI-Secretary
	if pd := os.Getenv("ProgramData"); pd != "" {
		fallback := filepath.Join(pd, "AI-Secretary")
		if fileExists(filepath.Join(fallback, "docker-compose.yml")) {
			return fallback
		}
	}
	return dir
}

func fileExists(p string) bool {
	_, err := os.Stat(p)
	return err == nil
}

// runCmd 在项目目录执行命令并返回 stdout+stderr 合并。
func runCmd(ctx context.Context, name string, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, name, args...)
	cmd.Dir = projectDir()
	hideWindow(cmd) // Windows 下隐藏黑窗
	out, err := cmd.CombinedOutput()
	return string(out), err
}

// dockerReady 检查 docker daemon 是否在响应
func dockerReady(ctx context.Context) bool {
	cctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	_, err := runCmd(cctx, "docker", "info")
	return err == nil
}

// startDockerDesktop 尝试拉起 Docker Desktop（仅 Windows/Mac），等待 daemon 起来。
func startDockerDesktop(ctx context.Context) error {
	if dockerReady(ctx) {
		return nil
	}
	log.Println("Docker daemon 未响应，尝试启动 Docker Desktop...")

	switch runtime.GOOS {
	case "windows":
		// 标准安装路径
		candidates := []string{
			`C:\Program Files\Docker\Docker\Docker Desktop.exe`,
			filepath.Join(os.Getenv("ProgramFiles"), `Docker\Docker\Docker Desktop.exe`),
		}
		for _, p := range candidates {
			if fileExists(p) {
				cmd := exec.Command(p)
				_ = cmd.Start()
				break
			}
		}
	case "darwin":
		_ = exec.Command("open", "-a", "Docker").Start()
	}

	// 等 daemon 起来，最多 90 秒
	deadline := time.Now().Add(90 * time.Second)
	for time.Now().Before(deadline) {
		if dockerReady(ctx) {
			log.Println("Docker daemon 已就绪")
			return nil
		}
		time.Sleep(2 * time.Second)
	}
	return fmt.Errorf("Docker Desktop 启动超时（90s）")
}

// composeUp 启动所有服务
func composeUp(ctx context.Context) error {
	out, err := runCmd(ctx, "docker", "compose", "up", "-d")
	if err != nil {
		return fmt.Errorf("docker compose up 失败: %v\n%s", err, out)
	}
	log.Println("compose up 输出:\n" + out)
	return nil
}

// composeDown 停止所有服务
func composeDown(ctx context.Context) error {
	out, err := runCmd(ctx, "docker", "compose", "down")
	if err != nil {
		return fmt.Errorf("docker compose down 失败: %v\n%s", err, out)
	}
	return nil
}

// composeRestart 重启
func composeRestart(ctx context.Context) error {
	out, err := runCmd(ctx, "docker", "compose", "restart")
	if err != nil {
		return fmt.Errorf("docker compose restart 失败: %v\n%s", err, out)
	}
	log.Println("compose restart 输出:\n" + out)
	return nil
}

// waitHealthy 轮询 /health/ready
func waitHealthy(ctx context.Context, timeout time.Duration) bool {
	client := &http.Client{Timeout: 3 * time.Second}
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		resp, err := client.Get(healthURL)
		if err == nil {
			code := resp.StatusCode
			resp.Body.Close()
			if code == 200 {
				return true
			}
		}
		select {
		case <-ctx.Done():
			return false
		case <-time.After(3 * time.Second):
		}
	}
	return false
}

// runConfiguratorIfNeeded：第一次启动时（.env 缺失或没填关键字段）拉起配置向导。
func runConfiguratorIfNeeded() {
	envPath := filepath.Join(projectDir(), ".env")
	needConfig := !fileExists(envPath)
	if !needConfig {
		// 简单检查关键字段是否填了
		b, _ := os.ReadFile(envPath)
		s := string(b)
		needConfig = !strings.Contains(s, "ADMIN_PASSWORD_HASH=$2") ||
			strings.Contains(s, "SILICONFLOW_API_KEY=sk-your-key-here") ||
			strings.Contains(s, "SILICONFLOW_API_KEY=\n")
	}
	if !needConfig {
		return
	}

	cfg := filepath.Join(projectDir(), "configurator.exe")
	if !fileExists(cfg) {
		log.Println("未找到 configurator.exe，跳过首次配置向导")
		return
	}
	log.Println("首次启动，运行配置向导...")
	cmd := exec.Command(cfg)
	cmd.Dir = projectDir()
	_ = cmd.Run() // 阻塞直到用户填完关闭
}

// ============================================================
// 系统托盘
// ============================================================

func onReady() {
	systray.SetTitle("AI 首席参谋")
	systray.SetTooltip("AI 首席参谋（启动中…）")
	if iconBytes != nil {
		systray.SetIcon(iconBytes)
	}

	mOpen := systray.AddMenuItem("打开管理后台", "在浏览器中打开 http://localhost:8501")
	systray.AddSeparator()
	mRestart := systray.AddMenuItem("重启服务", "重启所有 Docker 容器")
	mLogs := systray.AddMenuItem("查看日志", "打开日志窗口")
	systray.AddSeparator()
	mStop := systray.AddMenuItem("停止服务", "停止所有容器（系统将不可用）")
	systray.AddSeparator()
	mQuit := systray.AddMenuItem("退出启动器", "保留服务后台运行，仅退出托盘")

	// 后台启动流程
	go func() {
		ctx := context.Background()
		runConfiguratorIfNeeded()

		if err := startDockerDesktop(ctx); err != nil {
			systray.SetTooltip("AI 首席参谋（Docker 未就绪：" + err.Error() + "）")
			notify("启动失败", "Docker Desktop 未能启动：\n"+err.Error())
			return
		}

		systray.SetTooltip("AI 首席参谋（启动容器中…）")
		if err := composeUp(ctx); err != nil {
			systray.SetTooltip("AI 首席参谋（启动失败）")
			notify("启动失败", err.Error())
			return
		}

		systray.SetTooltip("AI 首席参谋（等待健康检查…）")
		if waitHealthy(ctx, startupWait) {
			systray.SetTooltip("AI 首席参谋（运行中）")
			_ = open.Run(uiURL)
			notify("已启动", "AI 首席参谋已就绪，浏览器已为你打开。")
		} else {
			systray.SetTooltip("AI 首席参谋（健康检查超时）")
			notify("启动慢", "服务还在启动中，过会儿在托盘图标右键 → 打开管理后台。")
		}
	}()

	// 菜单事件循环
	for {
		select {
		case <-mOpen.ClickedCh:
			_ = open.Run(uiURL)
		case <-mRestart.ClickedCh:
			go func() {
				systray.SetTooltip("AI 首席参谋（重启中…）")
				if err := composeRestart(context.Background()); err != nil {
					notify("重启失败", err.Error())
					return
				}
				if waitHealthy(context.Background(), startupWait) {
					systray.SetTooltip("AI 首席参谋（运行中）")
					notify("已重启", "服务已恢复。")
				}
			}()
		case <-mLogs.ClickedCh:
			openLogs()
		case <-mStop.ClickedCh:
			go func() {
				systray.SetTooltip("AI 首席参谋（停止中…）")
				if err := composeDown(context.Background()); err != nil {
					notify("停止失败", err.Error())
					return
				}
				systray.SetTooltip("AI 首席参谋（已停止）")
				notify("已停止", "所有容器已停止。下次双击图标可重新启动。")
			}()
		case <-mQuit.ClickedCh:
			systray.Quit()
			return
		}
	}
}

func onExit() {
	// 退出托盘不停容器；用户想停服务点"停止"菜单。
}

// openLogs：在新终端窗口跑 docker compose logs -f fastapi
func openLogs() {
	dir := projectDir()
	switch runtime.GOOS {
	case "windows":
		// /K 让窗口保持开着；用 powershell 是为了 UTF-8 中文不乱码
		cmd := exec.Command("cmd.exe", "/C", "start", "powershell",
			"-NoExit", "-Command",
			fmt.Sprintf("cd '%s'; docker compose logs -f fastapi", dir))
		_ = cmd.Start()
	case "darwin":
		script := fmt.Sprintf(`tell application "Terminal" to do script "cd %s && docker compose logs -f fastapi"`, dir)
		_ = exec.Command("osascript", "-e", script).Start()
	}
}

func main() {
	// 日志写到 %ProgramData%\AI-Secretary\launcher.log
	if pd := os.Getenv("ProgramData"); pd != "" {
		logPath := filepath.Join(pd, "AI-Secretary", "launcher.log")
		_ = os.MkdirAll(filepath.Dir(logPath), 0755)
		if f, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644); err == nil {
			log.SetOutput(f)
		}
	}
	log.Println("=== launcher 启动 ===")
	log.Println("项目目录:", projectDir())

	systray.Run(onReady, onExit)
}
