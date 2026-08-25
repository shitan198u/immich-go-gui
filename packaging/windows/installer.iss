#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif

#ifndef MyNumericVersion
#define MyNumericVersion "1.0.0.0"
#endif

#ifndef MyOutputFilename
#define MyOutputFilename "Immich-Go-GUI-Windows-Setup"
#endif

[Setup]
AppName=Immich-Go GUI
AppVersion={#MyAppVersion}
AppPublisher=shitan198u
AppPublisherURL=https://github.com/shitan198u/immich-go-gui
AppSupportURL=https://github.com/shitan198u/immich-go-gui/issues
AppUpdatesURL=https://github.com/shitan198u/immich-go-gui/releases
AppComments=Desktop GUI for immich-go bulk media operations
AppCopyright=Copyright (C) 2026 shitan198u
DefaultDirName={autopf}\Immich-Go GUI
DefaultGroupName=Immich-Go GUI
UninstallDisplayIcon={app}\Immich-Go-GUI.exe
SetupIconFile=..\..\immich-go-gui.ico
LicenseFile=..\..\LICENSE.txt
Compression=lzma2
SolidCompression=yes
SourceDir=..\..\
OutputDir=..\..\
OutputBaseFilename={#MyOutputFilename}
VersionInfoVersion={#MyNumericVersion}
VersionInfoCompany=shitan198u
VersionInfoDescription=Immich-Go GUI Installer
VersionInfoProductName=Immich-Go GUI
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) 2026 shitan198u

[Files]
Source: "app.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Immich-Go GUI"; Filename: "{app}\Immich-Go-GUI.exe"
Name: "{autodesktop}\Immich-Go GUI"; Filename: "{app}\Immich-Go-GUI.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
