# <img src="{ico_link}" width="40" align="center"> {name}
***{name}*** wraps ***[Sfvip Player](https://github.com/K4L4Uz/SFVIP-Player/tree/master)*** with a local proxy that inserts an _All_ category into _Live_, _Series_ and _Vod_.  
So you can easily **search your entire catalog**. It also **updates [mpv player](https://mpv.io/)** dll so you can enjoy its lastest features.

<img src="resources/all.png">

# Download
[<img src="https://img.shields.io/badge/{name} {version} x64-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://img.shields.io/badge/{exe_x86_clean}?style=flat-square" height="30">](https://github.com/{github_path}/raw/master/{exe_x64_link})<img src="https://custom-icon-badges.demolab.com/badge/Scanned by Microsoft Defender • {exe_x64_engine} • {exe_x64_signature}-white.svg?logo=shield-check&logoColor=black&style=flat-square" height="15">

[<img src="https://img.shields.io/badge/{name} {version} x86-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://img.shields.io/badge/{exe_x86_clean}?style=flat-square" height="30">](https://github.com/{github_path}/raw/master/{exe_x86_link})<img src="https://custom-icon-badges.demolab.com/badge/Scanned by Microsoft Defender • {exe_x86_engine} • {exe_x86_signature}-white.svg?logo=shield-check&logoColor=black&style=flat-square" height="15">

Check the [***changelog***](build/changelog.md) and ***notes***[^1].  
Get [***SfvipUserProxy***](user_proxy_cmd) _command line_ to add or remove an user proxy for ***all users*** in ***Sfvip Player*** database.

[^1]:_**{name}** will ask you for network connection its first run because it relies on local proxies to do its magic._  
_On **old systems** you might need to install [**vc redist**](https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist) for [**x86**](https://aka.ms/vs/17/release/vc_redist.x86.exe) or [**x64**](https://aka.ms/vs/17/release/vc_redist.x64.exe)._  

# Build
[![Python](https://img.shields.io/badge/Python-{py_version}-fbdf79?logo=python&logoColor=fbdf79)](https://www.python.org/downloads/release/python-{py_version_compact}/)
[![Nuitka](https://img.shields.io/badge/Nuitka-{nuitka_version}-informational)](https://nuitka.net/)
[![Nsis](https://img.shields.io/badge/Nsis-{nsis_version}-informational)](https://nsis.sourceforge.io/Download)
[![mitmproxy](https://img.shields.io/badge/Mitmproxy-{mitmproxy_version}-informational)](https://mitmproxy.org/)
[![Style](https://img.shields.io/badge/Style-Black-000000)](https://black.readthedocs.io/en/stable/)
![Sloc](https://img.shields.io/badge/Sloc-{sloc}-informational)

[***NSIS***](https://nsis.sourceforge.io/Download) will be automatically installed if missing.  
Check the [***build config***](build_config.py).
### Create an x64 environment
With [***Python {py_version} x64***](https://www.python.org/ftp/python/{py_version}/python-{py_version}-amd64.exe) or above.  
```console
python -m venv {env_x64}
{env_x64}\scripts\activate
python -m pip install {requirements_x64}
```
Set ***{env_x64_decl}*** appropriately if you use a different environement.  
### Create an x86 environment
With [***Python {py_version} x86***](https://www.python.org/ftp/python/{py_version}/python-{py_version}.exe) or above.  
```console
python -m venv {env_x86}
{env_x86}\scripts\activate
python -m pip install {requirements_x86}
```
Set ***{env_x86_decl}*** appropriately if you use a different environement.  
### Run locally
```console
python -m {script_main}
```
### Build with ***Mingw64***
_The easiest option._
```console
python -m dev.build --mingw
```
### Build with ***Clang***
_The recommended option._
```console
python -m dev.build
```
You need [**Visual Studio Community Edition**](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx) with those [**components**](resources/.vsconfig):

<img src="resources/VS.png">

### Build specific versions
```console
python -m dev.build [--x86 | --x64 | --both] [--nobuild | --noinstaller | --readme] [--upgrade] [--publish] [--mingw]
```
### Upgrade dependencies
```console
python -m dev.upgrade [--x86 | --x64 | --both] [--noeager]
```
### Publish an update
```console
python -m dev.publish [--x86 | --x64 | --both] [--version VERSION] [--info]
```
### Scan for virus
```console
python -m dev.scan [--x86 | --x64 | --both]
```

### Translations
You need a [***DeepL API key***](https://www.deepl.com/en/docs-api/).
```console
python -m dev.translate [--force] [--language LANGUAGE]
```
