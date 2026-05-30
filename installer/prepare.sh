#!/usr/bin/env bash
# 在维护者电脑上一键准备所有产物到 installer/ 下，供 Inno Setup 编译
#
# 前置：本机已装 Go 1.22+；CGO 工具链（Fyne 需要）：
#   Windows: tdm-gcc 或 mingw-w64
#   Mac/Linux: 默认的 cc 即可
#
# 用法（在仓库根）:
#   bash installer/prepare.sh
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

INSTALLER="$ROOT/installer"
BIN="$INSTALLER/bin"
PAYLOAD="$INSTALLER/payload"

echo "==> 清理旧产物"
rm -rf "$BIN" "$PAYLOAD"
mkdir -p "$BIN" "$PAYLOAD"

# ============================================================
# 1. 编译 launcher.exe（系统托盘启动器）
# ============================================================
echo "==> 编译 launcher.exe"
(cd launcher && go mod tidy && \
    GOOS=windows GOARCH=amd64 \
    go build -ldflags "-H=windowsgui -s -w" -o "$BIN/AI首席参谋.exe" .)

# ============================================================
# 2. 编译 configurator.exe（首次配置向导）
# ============================================================
echo "==> 编译 configurator.exe"
echo "    注意：Fyne 需要 CGO，确保已装好 C 编译器（mingw-w64）"
(cd configurator && go mod tidy && \
    CGO_ENABLED=1 GOOS=windows GOARCH=amd64 \
    go build -ldflags "-H=windowsgui -s -w" -o "$BIN/configurator.exe" .)

# ============================================================
# 3. 复制图标
# ============================================================
ICON_SRC="$INSTALLER/assets/icon.ico"
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$BIN/icon.ico"
else
    echo "WARN: $ICON_SRC 不存在，请放置一个 256x256 的 .ico 图标"
fi

# ============================================================
# 4. 整理 payload（项目本体）
# ============================================================
echo "==> 整理 payload（项目文件）"
EXCLUDE_PATTERNS=(
    --exclude='.git/'
    --exclude='.github/'
    --exclude='__pycache__/'
    --exclude='*.pyc'
    --exclude='.venv/'
    --exclude='venv/'
    --exclude='node_modules/'
    --exclude='.idea/'
    --exclude='.vscode/'
    --exclude='installer/'
    --exclude='launcher/'
    --exclude='configurator/'
    --exclude='backups/'
    --exclude='.env'
    --exclude='.env.bak'
    --exclude='memory/'
    --exclude='*.log'
)

if command -v rsync >/dev/null 2>&1; then
    rsync -a "${EXCLUDE_PATTERNS[@]}" ./ "$PAYLOAD/"
else
    # 兜底：用 cp 然后删除排除项
    cp -r ./. "$PAYLOAD/"
    rm -rf "$PAYLOAD/.git" "$PAYLOAD/.github" "$PAYLOAD/installer" \
           "$PAYLOAD/launcher" "$PAYLOAD/configurator" \
           "$PAYLOAD/backups" "$PAYLOAD/memory" "$PAYLOAD/.env" 2>/dev/null || true
    find "$PAYLOAD" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
    find "$PAYLOAD" -name "*.pyc" -delete 2>/dev/null || true
fi

# 写入 VERSION（覆盖以保证最新）
[ -f VERSION ] && cp VERSION "$PAYLOAD/VERSION"

echo ""
echo "==> 准备完成"
echo "    bin/      : $(ls "$BIN")"
echo "    payload/  : $(du -sh "$PAYLOAD" | cut -f1)"
echo ""
echo "下一步: 用 Inno Setup Compiler 编译 installer/setup.iss"
echo "        生成的 Setup.exe 在 installer/dist/"
