//go:build windows

package main

import (
	"os/exec"
	"strings"
	"syscall"
)

// hideWindow 隐藏 docker.exe 子进程的黑色控制台窗口
func hideWindow(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow:    true,
		CreationFlags: 0x08000000, // CREATE_NO_WINDOW
	}
}

// notify 用 Windows 内置 BurntToast / msg.exe / PowerShell 发通知
func notify(title, body string) {
	// 用 PowerShell + Windows 通知中心
	script := `
$ErrorActionPreference = 'SilentlyContinue'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$xml = [xml]$template.GetXml()
$xml.toast.visual.binding.text[0].'#text' = '` + escapePS(title) + `'
$xml.toast.visual.binding.text[1].'#text' = '` + escapePS(body) + `'
$doc = New-Object Windows.Data.Xml.Dom.XmlDocument
$doc.LoadXml($xml.OuterXml)
$toast = New-Object Windows.UI.Notifications.ToastNotification $doc
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('AI首席参谋').Show($toast)
`
	cmd := exec.Command("powershell", "-NoProfile", "-NonInteractive",
		"-WindowStyle", "Hidden", "-Command", script)
	hideWindow(cmd)
	_ = cmd.Start()
}

func escapePS(s string) string {
	return strings.ReplaceAll(s, "'", "''")
}
