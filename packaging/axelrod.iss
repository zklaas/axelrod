; Inno Setup script: the Windows installer for Axelrod.
; Built by .github/workflows/release.yml from PyInstaller's dist\Axelrod folder:
;   iscc /DAppVersion=1.0.0 packaging\axelrod.iss
; Installs for the current user only (no administrator rights), adds a Start-menu
; entry and an uninstaller (Settings > Apps).

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{0C6207DD-7D00-47D5-BEF5-B0B2C9738400}
AppName=Axelrod
AppVersion={#AppVersion}
AppPublisher=Zachary Klaas
AppPublisherURL=https://github.com/zklaas/axelrod
DefaultDirName={localappdata}\Programs\Axelrod
DefaultGroupName=Axelrod
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=Axelrod-Setup-Windows
SetupIconFile=..\icons\axelrod.ico
UninstallDisplayIcon={app}\Axelrod.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\Axelrod\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Axelrod"; Filename: "{app}\Axelrod.exe"
Name: "{userdesktop}\Axelrod"; Filename: "{app}\Axelrod.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\Axelrod.exe"; Description: "Start Axelrod"; Flags: nowait postinstall skipifsilent
