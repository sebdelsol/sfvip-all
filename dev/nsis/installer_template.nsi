; https://stackoverflow.com/questions/2565215/checking-if-the-application-is-running-in-nsis-before-uninstalling
; TODO check alreadyrunning

!define PRODUCT_NAME "{name}"
!define PRODUCT_VERSION "{version}"
!define PRODUCT_PUBLISHER "{company}"

; modern
!include "MUI2.nsh"

Name "{name} {version} {bitness}"
OutFile "{name}.exe"
RequestExecutionLevel user
InstallDir "$LocalAppData\Programs\{name} {bitness}"
SetCompressor /SOLID bzip2 ; /SOLID lzma trigger AV...
Unicode true
ManifestDPIAware true
ShowInstDetails hide
ShowUninstDetails hide

!define MUI_ICON "{dist}\{ico}"
!define MUI_UNICON "{dist}\{ico}"
!if {finish_page}
    !define MUI_FINISHPAGE_RUN 
    !define MUI_FINISHPAGE_RUN_FUNCTION "RunApp"
!endif

!insertmacro MUI_PAGE_INSTFILES
!if {finish_page}
    !insertmacro MUI_PAGE_FINISH
!endif
!insertmacro MUI_UNPAGE_INSTFILES

; {languages}

Section
    SectionIn RO ; Read-only
    SetOverwrite ifnewer
    SetOutPath "$InstDir"
    File /r "{dist}"
    WriteUninstaller "$InstDir\uninstall.exe"
    ; Add/remove programs
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{name} {bitness}" "DisplayName" "{name} {bitness}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{name} {bitness}" "DisplayVersion" "{version}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{name} {bitness}" "DisplayIcon" "$InstDir\{dist}\{ico}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{name} {bitness}" "UninstallString" "$InstDir\uninstall.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{name} {bitness}" "InstallLocation" "$InstDir"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{name} {bitness}" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{name} {bitness}" "NoRepair" 1
    ; link working directory 
    SetOutPath "$InstDir\{dist}" 
    ; CreateShortCut "$DESKTOP\{name} {bitness}.lnk" "$InstDir\{dist}\{name}.exe"
    createShortCut "$SMPROGRAMS\{name} {bitness}.lnk" "$InstDir\{dist}\{name}.exe"
    !if {has_install_cmd}
        nsExec::ExecToLog '"$InstDir\{dist}\{install_cmd}" {install_cmd_arg}'
    !endif
SectionEnd

Section "Uninstall"
    !if {has_uninstall_cmd}
        nsExec::ExecToLog '"$InstDir\{dist}\{uninstall_cmd}" {uninstall_cmd_arg}'
    !endif
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{name} {bitness}"
    RMDir /r "$InstDir\{dist}"
    Delete "$InstDir\uninstall.exe"
    ; Delete "$DESKTOP\{name} {bitness}.lnk"
    Delete "$SMPROGRAMS\{name} {bitness}.lnk"
SectionEnd

!if {finish_page}
    Function RunApp
    ; exe working directory
    SetOutPath "$InstDir\{dist}"
    Exec "$InstDir\{dist}\{name}.exe"
    FunctionEnd
!endif