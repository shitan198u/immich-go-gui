#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif

#ifndef MyOutputFilename
#define MyOutputFilename "Immich-Go-GUI-Windows-Setup"
#endif

[Setup]
AppName=Immich-Go GUI
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\Immich-Go GUI
DefaultGroupName=Immich-Go GUI
UninstallDisplayIcon={app}\Immich-Go-GUI.exe
Compression=lzma2
SolidCompression=yes
SourceDir=..\..\
OutputDir=..\..\
OutputBaseFilename={#MyOutputFilename}

[Files]
Source: "app.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Immich-Go GUI"; Filename: "{app}\Immich-Go-GUI.exe"
Name: "{autodesktop}\Immich-Go GUI"; Filename: "{app}\Immich-Go-GUI.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
