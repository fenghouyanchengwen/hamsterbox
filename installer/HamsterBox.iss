#define MyAppName "HamsterBox"
#define MyAppVersion "0.1.0"
#define MyAppExeName "HamsterBox.exe"

[Setup]
AppId={{B75D8442-5F20-4F61-A2D4-62BD746D3021}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\HamsterBox
DefaultGroupName=仓鼠盒
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=HamsterBox-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"

[Files]
Source: "..\dist\HamsterBox\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\仓鼠盒"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\仓鼠盒"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动仓鼠盒"; Flags: postinstall nowait skipifsilent