// AI 首席参谋 首次配置向导
//
// 弹出 GUI 让用户填:
//  1. SiliconFlow API Key
//  2. 管理员登录密码（明文，会自动 bcrypt）
//
// 自动生成:
//   - APP_ENCRYPTION_KEY (Fernet)
//   - ADMIN_API_TOKEN (256-bit hex)
//   - ADMIN_PASSWORD_HASH (bcrypt)
//
// 写入: <项目目录>/.env
//
// 编译（Windows）:
//
//	cd configurator
//	go build -ldflags "-H=windowsgui -s -w" -o ../installer/configurator.exe
package main

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/widget"
	"golang.org/x/crypto/bcrypt"
)

// projectDir：configurator.exe 同目录或上级目录里有 docker-compose.yml 的那一层
func projectDir() string {
	exe, err := os.Executable()
	if err != nil {
		return "."
	}
	dir := filepath.Dir(exe)
	if _, err := os.Stat(filepath.Join(dir, "docker-compose.yml")); err == nil {
		return dir
	}
	parent := filepath.Dir(dir)
	if _, err := os.Stat(filepath.Join(parent, "docker-compose.yml")); err == nil {
		return parent
	}
	if pd := os.Getenv("ProgramData"); pd != "" {
		fb := filepath.Join(pd, "AI-Secretary")
		if _, err := os.Stat(filepath.Join(fb, "docker-compose.yml")); err == nil {
			return fb
		}
	}
	return dir
}

// generateFernetKey: 32 字节随机 → urlsafe base64
func generateFernetKey() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return base64.URLEncoding.EncodeToString(b), nil
}

// generateHexToken: n 字节随机 → hex
func generateHexToken(n int) (string, error) {
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

// hashPassword: bcrypt（默认 cost=12）
func hashPassword(plain string) (string, error) {
	h, err := bcrypt.GenerateFromPassword([]byte(plain), 12)
	if err != nil {
		return "", err
	}
	return string(h), nil
}

// writeEnv 把已生成的密钥 + 用户输入合并到 .env
//
// 策略：以 .env.example 为模板，整行替换关键字段。如果 .env 已存在，备份为 .env.bak。
func writeEnv(apiKey, adminPwd string) error {
	dir := projectDir()
	tmplPath := filepath.Join(dir, ".env.example")
	envPath := filepath.Join(dir, ".env")

	tmpl, err := os.ReadFile(tmplPath)
	if err != nil {
		return fmt.Errorf("找不到 .env.example: %w", err)
	}

	encKey, err := generateFernetKey()
	if err != nil {
		return err
	}
	adminToken, err := generateHexToken(32)
	if err != nil {
		return err
	}
	pwdHash, err := hashPassword(adminPwd)
	if err != nil {
		return err
	}

	replacements := map[string]string{
		"SILICONFLOW_API_KEY": apiKey,
		"APP_ENCRYPTION_KEY":  encKey,
		"ADMIN_API_TOKEN":     adminToken,
		"ADMIN_PASSWORD_HASH": pwdHash,
		"APP_ENV":             "production",
	}

	lines := strings.Split(string(tmpl), "\n")
	for i, line := range lines {
		trim := strings.TrimSpace(line)
		if trim == "" || strings.HasPrefix(trim, "#") {
			continue
		}
		for k, v := range replacements {
			if strings.HasPrefix(trim, k+"=") {
				lines[i] = k + "=" + v
				break
			}
		}
	}

	// 备份旧 .env
	if _, err := os.Stat(envPath); err == nil {
		_ = os.Rename(envPath, envPath+".bak")
	}

	return os.WriteFile(envPath, []byte(strings.Join(lines, "\n")), 0600)
}

func main() {
	a := app.NewWithID("com.ai-for-management.configurator")
	w := a.NewWindow("AI 首席参谋 — 首次配置")
	w.Resize(fyne.NewSize(620, 460))
	w.CenterOnScreen()

	title := widget.NewLabelWithStyle("欢迎使用 AI 首席参谋",
		fyne.TextAlignLeading, fyne.TextStyle{Bold: true})
	subtitle := widget.NewLabel("第一次启动需要配置 2 项内容。其余密钥将自动生成。")

	// 1. API Key
	apiKeyEntry := widget.NewPasswordEntry()
	apiKeyEntry.SetPlaceHolder("sk-xxxxxxxxxxxxxxxx")

	apiKeyHelp := widget.NewLabel(
		"还没有 API Key？请到 https://siliconflow.cn 注册（免费），\n" +
			"在「API 密钥」页面新建一个，复制粘贴到这里。")
	apiKeyHelp.Wrapping = fyne.TextWrapWord

	// 2. 管理员密码
	pwd1 := widget.NewPasswordEntry()
	pwd1.SetPlaceHolder("至少 12 位，含大小写和数字")
	pwd2 := widget.NewPasswordEntry()
	pwd2.SetPlaceHolder("再输一次确认")

	pwdHelp := widget.NewLabel(
		"这是你登录管理后台时用的密码。请用强密码并妥善保管。")
	pwdHelp.Wrapping = fyne.TextWrapWord

	// 表单
	form := widget.NewForm(
		widget.NewFormItem("SiliconFlow API Key", apiKeyEntry),
		widget.NewFormItem("", apiKeyHelp),
		widget.NewFormItem("管理员密码", pwd1),
		widget.NewFormItem("确认密码", pwd2),
		widget.NewFormItem("", pwdHelp),
	)

	statusLabel := widget.NewLabel("")

	saveBtn := widget.NewButton("保存配置并启动", func() {
		key := strings.TrimSpace(apiKeyEntry.Text)
		p1 := pwd1.Text
		p2 := pwd2.Text

		if err := validate(key, p1, p2); err != nil {
			dialog.ShowError(err, w)
			return
		}

		statusLabel.SetText("正在写入配置...")
		if err := writeEnv(key, p1); err != nil {
			dialog.ShowError(fmt.Errorf("写入 .env 失败: %w", err), w)
			statusLabel.SetText("")
			return
		}
		statusLabel.SetText("配置完成。窗口将自动关闭，启动器接管后续启动。")
		dialog.ShowInformation("配置成功",
			"密钥已生成并写入 .env。\n关闭此窗口后，启动器会自动启动 Docker 服务。",
			w)
		w.Close()
	})
	saveBtn.Importance = widget.HighImportance

	cancelBtn := widget.NewButton("退出（不保存）", func() {
		os.Exit(1)
	})

	buttons := container.NewHBox(saveBtn, cancelBtn)
	content := container.NewVBox(title, subtitle, widget.NewSeparator(),
		form, statusLabel, widget.NewSeparator(), buttons)

	w.SetContent(container.NewPadded(content))
	w.SetCloseIntercept(func() {
		// 关闭窗口 = 用户主动放弃；交回控制权给启动器
		os.Exit(1)
	})
	w.ShowAndRun()
}

func validate(apiKey, p1, p2 string) error {
	if !strings.HasPrefix(apiKey, "sk-") || len(apiKey) < 20 {
		return errors.New("SiliconFlow API Key 格式不对（应以 sk- 开头）")
	}
	if len(p1) < 8 {
		return errors.New("密码至少 8 位")
	}
	if p1 != p2 {
		return errors.New("两次输入的密码不一致")
	}
	return nil
}
