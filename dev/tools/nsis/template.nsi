VIProductVersion "{{version}}"
VIFileVersion "{{version}}"
VIAddVersionKey "FileVersion" "{{version}}"
VIAddVersionKey "ProductName" "{{name}}"
VIAddVersionKey "CompanyName" "{{company}}"

; modern UI
!include "MUI2.nsh"
Name "{{name}} {{version}} {{bitness}}"
OutFile "{{installer}}"
RequestExecutionLevel user
InstallDir "$LocalAppData\Programs\{{name}} {{bitness}}"
; bzip2 if it triggers AV
SetCompressor /SOLID lzma
Unicode true
ManifestDPIAware true
ShowInstDetails hide
ShowUninstDetails hide

!define MUI_ICON "{{dist}}\{{ico}}"
!define MUI_UNICON "{{dist}}\{{ico}}"

!insertmacro MUI_PAGE_INSTFILES
{% if finish_page %}
!define MUI_FINISHPAGE_RUN 
!define MUI_FINISHPAGE_RUN_FUNCTION "RunApp"
!insertmacro MUI_PAGE_FINISH
{% endif %}
!insertmacro MUI_UNPAGE_INSTFILES 

{% for lang in all_langs %}
!insertmacro MUI_LANGUAGE "{{lang}}"
{% endfor %}

{% for translation in already_running %}
LangString already_running ${LANG_{{translation.lang}}} "{{translation.text}}"
{% endfor %}

{% if is_64 %}
!define System "sysnative"
{% else %}
!define System "system32"
{% endif %}
!define PowerShell "$Windir\${System}\WindowsPowerShell\v1.0\powershell.exe"
!define GetProcess "Get-Process '{{name}}' -ErrorAction SilentlyContinue"
!define CheckPath "Where-Object {$_.Path -eq '$InstDir\{{dist}}\{{name}}.exe'}"

!macro AbortIfAppRunning
    retry:
        nsExec::ExecToStack "${PowerShell} exit (${GetProcess} | ${CheckPath}).Count"
        Pop $0
        StrCmp $0 "0" notRunning
            MessageBox MB_RETRYCANCEL|MB_ICONSTOP "$(already_running)" IDRETRY retry
            Abort
    notRunning:
!macroend

!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{name}} {{bitness}}"

Section "Install"
    !insertmacro AbortIfAppRunning
    SectionIn RO ; Read-only
    SetOverwrite ifdiff
    SetOutPath "$InstDir"
    File /r "{{dist}}"
    {% if has_logs %}
    CreateDirectory "$InstDir\{{dist}}\{{logs_dir}}"
    {% endif %}
    WriteUninstaller "$InstDir\uninstall.exe"
    ; Add/remove programs
    WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "{{name}} {{bitness}}"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "{{version}}"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$InstDir\{{dist}}\{{ico}}"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" "$InstDir\uninstall.exe"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$InstDir"
    WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
    ; exe working directory 
    SetOutPath "$InstDir\{{dist}}" 
    createShortCut "$SMPROGRAMS\{{name}} {{bitness}}.lnk" "$InstDir\{{dist}}\{{name}}.exe"
    {% if has_install_cmd %}
    nsExec::ExecToLog '"$InstDir\{{dist}}\{{install_cmd}}" {{install_cmd_arg}}'
    {% endif %}
SectionEnd

Section "Uninstall"
    !insertmacro AbortIfAppRunning
    {% if has_uninstall_cmd %}
    nsExec::ExecToLog '"$InstDir\{{dist}}\{{uninstall_cmd}}" {{uninstall_cmd_arg}}'
    {% endif %}
    DeleteRegKey HKCU "${UNINSTALL_KEY}"
    RMDir /r "$InstDir\{{dist}}"
    {% if has_logs %}
    RMDir /r "$InstDir\{{dist}}\{{logs_dir}}"
    {% endif %}
    Delete "$InstDir\uninstall.exe"
    Delete "$SMPROGRAMS\{{name}} {{bitness}}.lnk"
SectionEnd

{% if finish_page %}
Function RunApp
    ; exe working directory
    SetOutPath "$InstDir\{{dist}}"
    Exec "$InstDir\{{dist}}\{{name}}.exe"
FunctionEnd
{% endif %}

