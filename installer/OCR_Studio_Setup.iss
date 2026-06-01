; Inno Setup — instalator OCR Studio
; Uruchom po zbudowaniu EXE: scripts\build_installer.ps1

#define MyAppName "OCR Studio"
#define MyAppPublisher "Marek Zettel"
#define MyAppURL "https://github.com/zetmar-collab/ocr-studio"
#ifndef MyAppVersion
  #define MyAppVersion "0.1.8"
#endif

[Setup]
AppId={{A8F4E2B1-9C3D-4F5A-B6E7-1D2C3A4B5C6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename=OCR_Studio_Setup_{#MyAppVersion}
SetupIconFile=..\data\ocr_studio_icon.ico
UninstallDisplayIcon={app}\OCR Studio.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\OCR Studio.exe"; DestDir: "{app}"; DestName: "OCR Studio.exe"; Flags: ignoreversion
; Ikona (opcjonalnie w katalogu aplikacji)
Source: "..\data\ocr_studio_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\OCR Studio.exe"
Name: "{group}\Odinstaluj {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\OCR Studio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OCR Studio.exe"; Description: "Uruchom {#MyAppName}"; Flags: nowait postinstall skipifsilent
