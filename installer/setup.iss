; ============================================================
; AI 首席参谋 — Windows 安装包 (Inno Setup 脚本)
; ============================================================
; 编译方式:
;   1. 先按 BUILD.md 把 launcher.exe / configurator.exe 放进
;      installer\bin\ ，把项目文件释放到 installer\payload\
;   2. 用 Inno Setup Compiler 打开本文件，点编译
;   3. 输出: installer\dist\AI首席参谋-Setup-{Version}.exe

#define AppName "AI 首席参谋"
#define AppPublisher "AI For Management"
#define AppURL "https://github.com/AI-For-Management/ai-chief-of-staff"
#define AppExeName "AI首席参谋.exe"
#define AppVersion GetEnv("APP_VERSION")
#if AppVersion == ""
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{E8C7A1F0-9D2B-4F3E-B5C0-7A6E5D4C3B2A}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}/releases

; 安装到 ProgramData，全用户可用，且 Docker 卷映射不会因用户不同而错位
DefaultDirName={commonpf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes

; UAC 提权（安装 Docker / 写注册表需要）
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; 输出
OutputDir=dist
OutputBaseFilename=AI首席参谋-Setup-{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
SetupIconFile=bin\icon.ico
UninstallDisplayIcon={app}\bin\icon.ico

; 中文界面
ShowLanguageDialog=no

[Languages]
Name: "chs"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"
Name: "autostart"; Description: "开机自启动 AI 首席参谋"; GroupDescription: "启动选项:"; Flags: unchecked

[Files]
; ===== 启动器 + 配置器 =====
Source: "bin\AI首席参谋.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "bin\configurator.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "bin\icon.ico"; DestDir: "{app}\bin"; Flags: ignoreversion

; ===== 项目文件（docker-compose、代码、脚本、文档） =====
; payload\ 目录由 BUILD.md 描述的脚本生成（rsync 仓库内容，过滤 .git 等）
Source: "payload\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\bin\{#AppExeName}"; IconFilename: "{app}\bin\icon.ico"
Name: "{group}\管理后台"; Filename: "http://localhost:8501"; IconFilename: "{app}\bin\icon.ico"
Name: "{group}\卸载 {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\bin\{#AppExeName}"; IconFilename: "{app}\bin\icon.ico"; Tasks: desktopicon

[Registry]
; 开机自启（HKLM Run）
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\bin\{#AppExeName}"""; \
    Tasks: autostart; Flags: uninsdeletevalue

[Run]
; 安装完成后立刻启动
Filename: "{app}\bin\{#AppExeName}"; Description: "立即启动 AI 首席参谋"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; 卸载时先停掉 docker compose（避免容器锁住文件）
; 静默执行，错误不阻止卸载
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -WindowStyle Hidden -Command ""cd '{app}'; docker compose down 2>$null"""; \
    Flags: runhidden; RunOnceId: "ComposeDown"

[Code]
// 检查 Docker Desktop 是否已安装；没有就询问用户、引导下载
function IsDockerInstalled(): Boolean;
var
  Found: Boolean;
begin
  Found := FileExists(ExpandConstant('{commonpf}\Docker\Docker\Docker Desktop.exe'));
  if not Found then
    Found := FileExists(ExpandConstant('{pf}\Docker\Docker\Docker Desktop.exe'));
  Result := Found;
end;

procedure InitializeWizard();
begin
  // 占位
end;

function InitializeSetup(): Boolean;
var
  Answer: Integer;
begin
  Result := True;
  if not IsDockerInstalled() then
  begin
    Answer := MsgBox(
      '检测到本机尚未安装 Docker Desktop。' + #13#10 + #13#10 +
      'AI 首席参谋需要 Docker 运行所有服务。' + #13#10 + #13#10 +
      '点「是」打开 Docker 官方下载页面，安装完成后请重新运行本安装程序。' + #13#10 +
      '点「否」忽略并继续（你需要手动安装 Docker）。',
      mbConfirmation, MB_YESNO);
    if Answer = IDYES then
    begin
      ShellExec('open', 'https://www.docker.com/products/docker-desktop/',
        '', '', SW_SHOWNORMAL, ewNoWait, Answer);
      Result := False;  // 终止本次安装，让用户先装 Docker
    end;
    // 选 NO 则继续安装（Result 保持 True）
  end;
end;
