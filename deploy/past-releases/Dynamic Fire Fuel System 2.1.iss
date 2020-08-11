#define PackageName      "Dynamic Fire Fuel System"
#define PackageNameLong  "Dynamic Fire Fuel System"
#define Version          "2.1"
#define ReleaseType      "official"
#define CoreVersion      "6.0"
#define CoreReleaseAbbr  ""

#define ExtDir "C:\Program Files\LANDIS-II\v6\bin\extensions"
#define AppDir "C:\Program Files\LANDIS-II\v6\"
#define LandisPlugInDir "C:\Program Files\LANDIS-II\plug-ins"

#include "package (Setup section) v6.0.iss"


[Files]
; Unique ==> These two (2) .dlls together constitute the Dynamic Fire Fuel System extension.
; NB. The Landis.Extension.DynamicFuels.dll must be built separately and added to ..\..\src\bin\debug
; NB: Do not put an additional version number in the file name of these .dlls
; (The names of these .dlls are defined in the \src\*.csproj file for each extension)
Source: ..\..\src\bin\debug\Landis.Extension.DynamicFire.dll; DestDir: {#ExtDir}; Flags: replacesameversion
Source: ..\..\src\bin\debug\Landis.Extension.DynamicFuels.dll; DestDir: {#ExtDir}; Flags: replacesameversion

; Requisite auxiliary libraries
; NB. These libraries are used by other extensions and thus are never uninstalled.
; (There are no auxiliary libraries)


; Complete example for testing the extension
Source: ..\examples\*.txt; DestDir: {#AppDir}\examples\Dynamic Fire Fuel System; Flags: replacesameversion
Source: ..\examples\*.gis; DestDir: {#AppDir}\examples\Dynamic Fire Fuel System; Flags: replacesameversion
Source: ..\examples\*.bat; DestDir: {#AppDir}\examples\Dynamic Fire Fuel System; Flags: replacesameversion
Source: ..\examples\*.csv; DestDir: {#AppDir}\examples\Dynamic Fire Fuel System; Flags: replacesameversion


; LANDIS-II identifies the extensions with the info in these .txt file
; NB. New releases must modify the name of these file and the info in them

#define InfoTxta "Dynamic Fire Component 2.1.txt"
Source: {#InfoTxta}; DestDir: {#LandisPlugInDir}

#define InfoTxtb "Dynamic Fuel Component 2.1.txt"
Source: {#InfoTxtb}; DestDir: {#LandisPlugInDir}




[Run]
;; Run plug-in admin tool to add entries for each plug-in
#define PlugInAdminTool  CoreBinDir + "\Landis.PlugIns.Admin.exe"

Filename: {#PlugInAdminTool}; Parameters: "remove ""Dynamic Fire Component"" "; WorkingDir: {#LandisPlugInDir}
Filename: {#PlugInAdminTool}; Parameters: "add ""{#InfoTxta}"" "; WorkingDir: {#LandisPlugInDir}

Filename: {#PlugInAdminTool}; Parameters: "remove ""Dynamic Fuel Component"" "; WorkingDir: {#LandisPlugInDir}
Filename: {#PlugInAdminTool}; Parameters: "add ""{#InfoTxtb}"" "; WorkingDir: {#LandisPlugInDir}



[Code]
{ Check for other prerequisites during the setup initialization }
#include "package (Code section) v3.iss"


//-----------------------------------------------------------------------------

function InitializeSetup_FirstPhase(): Boolean;
begin
  Result := True
end;
