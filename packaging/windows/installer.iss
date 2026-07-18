#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif

[Setup]
AppName=Immich-Go GUI
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\Immich-Go GUI
DefaultGroupName=Immich-Go GUI
UninstallDisplayIcon={app}\app.exe
Compression=lzma2
SolidCompression=yes
SourceDir=..\..\
OutputDir=..\..\
OutputBaseFilename=Immich-Go-GUI-Windows-Setup

[Files]
Source: "app.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Immich-Go GUI"; Filename: "{app}\app.exe"
Name: "{autodesktop}\Immich-Go GUI"; Filename: "{app}\app.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
