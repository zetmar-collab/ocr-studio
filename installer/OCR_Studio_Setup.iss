; Inno Setup — instalator OCR Studio
; Uruchom po zbudowaniu EXE: scripts\build_installer.ps1

#define MyAppName "Studio OCR"
#define MyAppPublisher "Marek Zettel"
#define MyAppURL "https://github.com/zetmar-collab/ocr-studio"
#ifndef MyAppVersion
  #define MyAppVersion "0.2.2"
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
LicenseFile=..\LICENSE
InfoAfterFile=..\THIRD-PARTY-NOTICES.md
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Instalacja dla biezacego uzytkownika - bez UAC (jak wersja ze Sklepu). Mozna wybrac
; instalacje dla wszystkich uzytkownikow w oknie dialogowym.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Cala aplikacja w wariancie --onedir (exe + _internal z silnikiem OCR i slownikami).
Source: "..\dist\OCR Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\OCR Studio.exe"
Name: "{group}\Odinstaluj {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\OCR Studio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OCR Studio.exe"; Description: "Uruchom {#MyAppName}"; Flags: nowait postinstall skipifsilent
