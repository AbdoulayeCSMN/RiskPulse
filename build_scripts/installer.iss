; Inno Setup script pour RiskPulse
; Telecharge Inno Setup : https://jrsoftware.org/isdl.php
; Compile : iscc installer.iss
; Sortie : dist/installer/RiskPulse-Setup-1.0.0.exe

#define MyAppName       "RiskPulse"
#define MyAppVersion    "1.0.0"
#define MyAppPublisher  "C. Abdoulaye"
#define MyAppExeName    "RiskPulse.exe"

[Setup]
AppId={{8E5C2B4A-9D3F-4A1E-B7C8-2F1A5D6E8C9B}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/AbdoulayeCSMN/riskpulse
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
LicenseFile=..\LICENSE
OutputDir=..\dist\installer
OutputBaseFilename=RiskPulse-Setup-{#MyAppVersion}
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
MinVersion=10.0.17763

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french";  MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon";Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Bundle PyInstaller (one-folder mode)
Source: "..\dist\RiskPulse\*";       DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md";              DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE";                DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";                       Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}";             Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";                 Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\{#MyAppName}\data\cache"
Type: filesandordirs; Name: "{userappdata}\{#MyAppName}\data\logs"
; Note : on NE supprime PAS knowledge.db / preferences pour preserver
; les donnees utilisateur en cas de reinstall. L'utilisateur peut nettoyer
; manuellement via %APPDATA%\RiskPulse.
