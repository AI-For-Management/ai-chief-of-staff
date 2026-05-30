//go:build !windows

package main

import (
	"fmt"
	"os/exec"
)

func hideWindow(cmd *exec.Cmd) {
	// 非 Windows 不需要隐藏窗口
}

func notify(title, body string) {
	// macOS: osascript；Linux: notify-send（若装了）
	script := fmt.Sprintf(`display notification %q with title %q`, body, title)
	_ = exec.Command("osascript", "-e", script).Start()
	_ = exec.Command("notify-send", title, body).Start()
}
