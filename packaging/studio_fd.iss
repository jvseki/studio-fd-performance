#define AppName "Studio FD Performance"
#include "..\build\release_version.iss"
#define AppExeName "Studio FD Performance.exe"

[Setup]
AppId={{A71B7309-A7B7-4BDA-A1EC-26B673AEBC84}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Studio FD Performance
AppComments=Gestao do Studio, alunos, planos e WhatsApp
DefaultDirName={localappdata}\Programs\Studio FD Performance
DefaultGroupName={#AppName}
UsePreviousAppDir=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
DisableProgramGroupPage=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=..\assets\app.ico
OutputDir=..\release
OutputBaseFilename=StudioFDPerformance-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
InfoBeforeFile=LEIA_ANTES.txt

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Area de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\Studio FD Performance\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent

; Nao ha UninstallDelete: os dados ficam fora de {app} e sao preservados.

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  VersionMS, VersionLS: Cardinal;
begin
  Result := '';
  if GetVersionNumbers(ExpandConstant('{app}\{#AppExeName}'), VersionMS, VersionLS) then
    if (VersionMS > {#VersionMS}) or ((VersionMS = {#VersionMS}) and (VersionLS > {#VersionLS})) then
      Result := 'Ja existe uma versao mais recente nesta pasta. Use o instalador mais recente.';
end;
