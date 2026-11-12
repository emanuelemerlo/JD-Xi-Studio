; JD-Xi Studio installer (Inno Setup 6). Built by the Windows build workflow:
;   iscc /DMyAppVersion=x.y.z jdxi_editor.iss      -> dist\installer\
; JD-Xi Studio has its own name, AppId and folder, so it never replaces (or is
; replaced by) the original JDXI-Editor: the two can be installed side by side.
#define MyAppName "JD-Xi Studio"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0a3"
#endif
#define MyAppPublisher "Emanuele Merlo"
#define MyAppURL "https://github.com/emanuelemerlo/JD-Xi-Studio"
#define MyAppExeName "JD-Xi-Studio.exe"
#define MyAppAssocName "JD-Xi SysEx file"
#define MyAppAssocExt ".syx"
#define MyAppAssocKey "JDXiStudio.syx"

[Setup]
; JD-Xi Studio's own AppId (up to 1.0.0a2 the installer still used the original
; program's {B248A955-...}: see [Code] below for the leftovers of that one)
AppId={{E7EDA7DB-0FD6-4825-9773-9599101296A8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppComments=An editor for the Roland JD-Xi, based on JDXI-Editor by Mark Brooks
DefaultDirName={localappdata}\Programs\JD-Xi Studio
DefaultGroupName={#MyAppName}
ChangesAssociations=yes
DisableProgramGroupPage=yes
; For the current user: no administrator rights
PrivilegesRequired=lowest
OutputBaseFilename=JD-Xi-Studio-{#MyAppVersion}-setup-win64
OutputDir=dist\installer
SetupIconFile=resources\jdxi_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
WizardImageFile=resources\installer_side.bmp
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; An update replaces the whole program: files of an older version (pictures,
; libraries) must not stay behind next to the new ones
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\JD-Xi-Studio\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\JD-Xi-Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".syx"; ValueData: ""

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// JD-Xi Studio 1.0.0a1 and a2 were installed with the original program's AppId
// and folder ("JDXI Editor" in %LOCALAPPDATA%\Programs\jdxi_editor). When that
// installation is JD-Xi Studio's (it has the Italian translation, which the
// original does not), offer to remove it, so the user does not keep two copies.
const
  OldKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{B248A955-5352-4AEA-8714-C272CF81910F}_is1';

function OldStudioUninstaller(var Cmd: String): Boolean;
var
  Location: String;
begin
  Result := False;
  if RegQueryStringValue(HKCU, OldKey, 'UninstallString', Cmd) and
     RegQueryStringValue(HKCU, OldKey, 'InstallLocation', Location) then
    // only JD-Xi Studio's alphas have the Italian interface; the original JDXI-Editor does not
    Result := FileExists(AddBackslash(Location) + '_internal\jdxi_editor\i18n\jdxi_editor_it.qm');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Cmd: String;
  Code: Integer;
begin
  if (CurStep = ssInstall) and OldStudioUninstaller(Cmd) then
  begin
    if SuppressibleMsgBox(ExpandConstant('{cm:UninstallOldStudio}'), mbConfirmation, MB_YESNO, IDYES) = IDYES then
      Exec(RemoveQuotes(Cmd), '/VERYSILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_HIDE, ewWaitUntilTerminated, Code);
  end;
end;

[CustomMessages]
english.UninstallOldStudio=An earlier JD-Xi Studio alpha is installed as "JDXI Editor". Remove it? (Your settings, programs and recipes are kept.)
italian.UninstallOldStudio=È installata una alpha precedente di JD-Xi Studio come "JDXI Editor". Vuoi rimuoverla? (Impostazioni, programmi e ricette restano.)
