package main

import (
	"os"
	"path/filepath"
)

// iconBytes 在启动时从 exe 同目录的 icon.ico 加载。
// 找不到则使用 nil（systray 会用默认图标）。
var iconBytes []byte

func init() {
	if exe, err := os.Executable(); err == nil {
		candidates := []string{
			filepath.Join(filepath.Dir(exe), "icon.ico"),
			filepath.Join(filepath.Dir(exe), "assets", "icon.ico"),
		}
		for _, p := range candidates {
			if b, err := os.ReadFile(p); err == nil {
				iconBytes = b
				return
			}
		}
	}
}
