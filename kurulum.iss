; ═══════════════════════════════════════════════════════════
;  Spor Tahmin — Inno Setup Kurulum Betiği
;  Profesyonel kurulum paketi: masaüstü kısayolu, başlat menüsü,
;  kaldırma desteği, sürüm bilgisi
; ═══════════════════════════════════════════════════════════

#define UygulamaAdi "Spor Tahmin"
#define UygulamaSurum "6.3"
#define UygulamaYayinci "CyberWolfSec"
#define UygulamaExe "SporTahmin.exe"

[Setup]
AppId={{8F3A5C21-9D74-4B6E-A2F1-7C8E9D0B3A45}
AppName={#UygulamaAdi}
AppVersion={#UygulamaSurum}
AppVerName={#UygulamaAdi} {#UygulamaSurum}
AppPublisher={#UygulamaYayinci}
AppPublisherURL=https://cyberwolfsec.com
AppSupportURL=https://cyberwolfsec.com
DefaultDirName={autopf}\{#UygulamaAdi}
DefaultGroupName={#UygulamaAdi}
DisableProgramGroupPage=yes
LicenseFile=KULLANIM.txt
OutputDir=kurulum_cikti
OutputBaseFilename=SporTahmin_Kurulum
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#UygulamaAdi}
UninstallDisplayIcon={app}\{#UygulamaExe}
VersionInfoVersion={#UygulamaSurum}.0.0.0
VersionInfoCompany={#UygulamaYayinci}
VersionInfoDescription={#UygulamaAdi} Kurulum
VersionInfoProductName={#UygulamaAdi}
VersionInfoProductVersion={#UygulamaSurum}

[Languages]
Name: "turkce"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "masaustu"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Kısayollar:"
Name: "baslatmenu"; Description: "Başlat menüsüne ekle"; GroupDescription: "Kısayollar:"; Flags: checkedonce

[Files]
Source: "dist\{#UygulamaExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "KULLANIM.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#UygulamaAdi}"; Filename: "{app}\{#UygulamaExe}"
Name: "{group}\Kaldır {#UygulamaAdi}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#UygulamaAdi}"; Filename: "{app}\{#UygulamaExe}"; Tasks: masaustu

[Run]
Filename: "{app}\{#UygulamaExe}"; Description: "{cm:LaunchProgram,{#UygulamaAdi}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
