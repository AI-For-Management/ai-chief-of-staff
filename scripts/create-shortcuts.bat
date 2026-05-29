@echo off
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0\.."
set "PROJECT_DIR=%cd%"

title 创建桌面快捷方式

echo.
echo 正在创建桌面快捷方式...
echo.

set "DESKTOP=%USERPROFILE%\Desktop"

REM 启动快捷方式
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $sc = $ws.CreateShortcut('%DESKTOP%\AI首席参谋-启动.lnk'); ^
   $sc.TargetPath = '%PROJECT_DIR%\start.bat'; ^
   $sc.WorkingDirectory = '%PROJECT_DIR%'; ^
   $sc.IconLocation = '%SystemRoot%\System32\shell32.dll,13'; ^
   $sc.Description = 'AI Chief of Staff 启动'; ^
   $sc.Save()"

REM 停止快捷方式
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $sc = $ws.CreateShortcut('%DESKTOP%\AI首席参谋-停止.lnk'); ^
   $sc.TargetPath = '%PROJECT_DIR%\stop.bat'; ^
   $sc.WorkingDirectory = '%PROJECT_DIR%'; ^
   $sc.IconLocation = '%SystemRoot%\System32\shell32.dll,131'; ^
   $sc.Description = 'AI Chief of Staff 停止'; ^
   $sc.Save()"

echo ✅ 已在桌面创建：
echo    - AI首席参谋-启动.lnk
echo    - AI首席参谋-停止.lnk
echo.
pause
