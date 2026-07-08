; Inno Setup スクリプト — MediaConv setup.exe を生成する
;
; 前提:
;   1. PyInstaller でビルド済み  ->  dist\MediaConv\ が存在
;   2. bin\ffmpeg.exe を配置済み（音声変換用）
; コンパイル:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
; 出力:
;   Output\MediaConv_setup.exe

#define MyAppName "MediaConv"
#define MyAppVersion "1.1"
#define MyAppPublisher "taise"
#define MyAppExeName "MediaConv.exe"

[Setup]
AppId={{6D1F2A93-4C7E-4B5A-9E20-MEDIACONV001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\MediaConv
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=MediaConv_setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加アイコン:"

[Files]
; アプリ本体（PyInstaller の出力一式）
Source: "dist\MediaConv\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; 同梱外部ツール（ffmpeg — 音声変換用）
Source: "bin\*"; DestDir: "{app}\bin"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
