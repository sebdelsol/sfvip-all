VIProductVersion "{{version}}"
VIFileVersion "{{version}}"
VIAddVersionKey "FileVersion" "{{version}}"
VIAddVersionKey "ProductName" "{{name}}"
VIAddVersionKey "CompanyName" "{{company}}"

!include "MUI2.nsh" ; modern UI
!include "FileFunc.nsh" ; GetParameters and GetOptions
Name "{{name}} {{version}} {{bitness}}"
OutFile "{{installer}}"
RequestExecutionLevel user
InstallDir "$LocalAppData\Programs\{{name}} {{bitness}}"
SetCompressor /SOLID {{compression}}
Unicode true
ManifestDPIAware true
ShowInstDetails hide
ShowUninstDetails hide

!define MUI_ICON "{{dist}}\{{ico}}"
!define MUI_UNICON "{{dist}}\{{ico}}"

; -------------
; directory page
; -------------
!define MUI_PAGE_CUSTOMFUNCTION_PRE "SetInstDir"
!insertmacro MUI_PAGE_DIRECTORY

; -------------
; install pages
; -------------
!define MUI_PAGE_CUSTOMFUNCTION_PRE "UninstallOldVersionIfNeeded"
Page Custom old.AppRunningPage old.AppRunningPageFinalize
Page Custom AppRunningPage AppRunningPageFinalize
!insertmacro MUI_PAGE_INSTFILES

; -------------
; finish pages
; -------------
{% if finish_page %}
Function RunApp
    SetOutPath "$InstDir\{{dist}}" ; exe working directory
    Exec "$InstDir\{{dist}}\{{name}}.exe"
FunctionEnd

Function AbortFinishPage
    ; Abort if /AUTORUN=yes
    ${GetParameters} $0
    ${GetOptions} $0 "/AUTORUN=" $1
    ClearErrors
    ${If} $1 == "yes"
        Call RunApp
        Abort
    ${Endif}
FunctionEnd

!define MUI_PAGE_CUSTOMFUNCTION_PRE "AbortFinishPage"
!define MUI_FINISHPAGE_RUN 
!define MUI_FINISHPAGE_RUN_FUNCTION "RunApp"
!insertmacro MUI_PAGE_FINISH
{% endif %}

; ---------------
; uninstall page
; ---------------
UninstPage Custom un.AppRunningPage un.AppRunningPageFinalize
!insertmacro MUI_UNPAGE_INSTFILES 

; ---------
; Languages
; ---------
; include all languages
{% for lang in all_languages %}
!insertmacro MUI_LANGUAGE "{{lang.name}}"
{% endfor %}

; already_running & retry translations
{% for lang in all_languages %}
LangString already_running ${LANG_{{lang.upper}}} "{{lang.already_running}}"
LangString retry ${LANG_{{lang.upper}}} "{{lang.retry}}"
{% endfor %}

; Cmd argument /LANG= to force the language (case insensitive)
!include "StrFunc.nsh" ; StrCase
${Using:StrFunc} StrCase

Function .onInit
    ${GetParameters} $0
    ${GetOptions} $0 "/LANG=" $1
    ${StrCase} $2 $1 "U"
    ${Switch} $2
        {% for lang in all_languages %}
        ${Case} "{{lang.upper}}"
            StrCpy $LANGUAGE ${LANG_{{lang.upper}}}
            ${Break}
        {% endfor %}
    ${EndSwitch}
FunctionEnd

; ---------------------
; AppRunning Page
; ---------------------
{% if is_64 %}
!define System "sysnative"
{% else %}
!define System "system32"
{% endif %}
!define PowerShell "$Windir\${System}\WindowsPowerShell\v1.0\powershell.exe"
!define GetProcess "Get-Process '{{name}}' -ErrorAction SilentlyContinue"

var NbAppRunning
var OldInstDir

!macro GetNbAppRunning old
    ; MessageBox MB_OK "old=`${old}`"
    !if `${old}` == "old."
        StrCpy $0 "Where-Object {$_.Path -eq '$OldInstDir\{{dist}}\{{name}}.exe'}"
    !else
        StrCpy $0 "Where-Object {$_.Path -eq '$InstDir\{{dist}}\{{name}}.exe'}"
    !endif
    nsExec::ExecToStack "${PowerShell} exit (${GetProcess} | $0).Count"
    Pop $0
    StrCpy $NbAppRunning $0
!macroend

!define FLASH_DELAY 500
!define LABEL_COLOR 0x000000            
!define LABEL_COLOR_FLASH 0xFF0000

var AlreadyRunning
var NextButton

!macro AlreadyRunningAndNext color enable
    ShowWindow $AlreadyRunning ${SW_HIDE}
    SetCtlColors $AlreadyRunning ${color} "transparent"    
    ShowWindow $AlreadyRunning ${SW_SHOW}
    EnableWindow $NextButton ${enable}
!macroend

!macro AppRunningPageMacro un old
    Function ${un}${old}AppRunningPage
        !insertmacro GetNbAppRunning `${old}`
        ${If} $NbAppRunning > 0
            nsDialogs::Create 1018
            ; next button
            GetDlgItem $NextButton $hWndParent 1 
            SendMessage $NextButton ${WM_SETTEXT} 0 "STR:$(retry)"
            ; AlreadyRunning label
            ${NSD_CreateLabel} 0 25% 100% 75% "$(already_running)"
            Pop $AlreadyRunning
            CreateFont $1 "Arial" 20
            SendMessage $AlreadyRunning ${WM_SETFONT} $1 1
            ${NSD_AddStyle} $AlreadyRunning ${SS_CENTER}
            ; header & AlreadyRunning label color
            !insertmacro MUI_HEADER_TEXT "$(^NameDA)" "$(already_running)"
            !insertmacro AlreadyRunningAndNext ${LABEL_COLOR} 1
            nsDialogs::Show
        ${EndIf}
    FunctionEnd

    Function ${un}${old}AppRunningPageFinalize
        ${NSD_CreateTimer} ${un}${old}FlashAlreadyRunningBegin 1
        !insertmacro GetNbAppRunning `${old}`
        ${If} $NbAppRunning > 0
            Abort ; stay on the page if running
        ${EndIf}
    FunctionEnd

    Function ${un}${old}FlashAlreadyRunningBegin
        ${NSD_KillTimer} ${un}${old}FlashAlreadyRunningBegin
        !insertmacro AlreadyRunningAndNext ${LABEL_COLOR_FLASH} 0
        ${NSD_CreateTimer} ${un}${old}FlashAlreadyRunningEnd ${FLASH_DELAY}
    FunctionEnd

    Function ${un}${old}FlashAlreadyRunningEnd
        ${NSD_KillTimer} ${un}${old}FlashAlreadyRunningEnd
        !insertmacro AlreadyRunningAndNext ${LABEL_COLOR} 1
    FunctionEnd
!macroend

!insertmacro AppRunningPageMacro "" "old."
!insertmacro AppRunningPageMacro "" ""
!insertmacro AppRunningPageMacro "un." ""

; ------------
; Install Page
; ------------
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{name}} {{bitness}}"

Section "Install"
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
    SetOutPath "$InstDir\{{dist}}" ; exe working directory 
    createShortCut "$SMPROGRAMS\{{name}} {{bitness}}.lnk" "$InstDir\{{dist}}\{{name}}.exe"
    {% if has_install_cmd %}
    nsExec::ExecToLog '"$InstDir\{{dist}}\{{install_cmd}}" {{install_cmd_arg}}'
    {% endif %}
SectionEnd

; --------------
; UnInstall Page
; --------------
Section "Uninstall"
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

; --------------
; Set install directory if in the registry
; --------------
Function SetInstDir
    ; check in the registry for already installed version
    ReadRegStr $0 HKCU "${UNINSTALL_KEY}" "InstallLocation"
    ${If} ${Errors}
        ClearErrors
    ${Else}
        StrCpy $InstDir $0
    ${Endif}
    ; save $InstDir
    StrCpy $OldInstDir $InstDir
    ; no directory page if /AUTOINSTDIR=yes
    ${GetParameters} $0
    ${GetOptions} $0 "/AUTOINSTDIR=" $1
    ClearErrors
    ${If} $1 == "yes"
        Abort
    ${Endif}
FunctionEnd

; --------------
; Uninstall version stored in the registry if different from instdir
; --------------
Function UninstallOldVersionIfNeeded
    ReadRegStr $0 HKCU "${UNINSTALL_KEY}" "InstallLocation"
    ${If} ${Errors}
        ClearErrors
    ${ElseIf} $InstDir != $0
        ${If} ${FileExists} "$0\uninstall.exe"
            ExecWait "$0\uninstall.exe /S"
        ${EndIf}
    ${Endif}
FunctionEnd
