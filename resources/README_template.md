# <img src="{ico_link}" width="40" align="center"> {name}
***{name}*** wraps ***[Sfvip Player](https://github.com/K4L4Uz/SFVIP-Player/tree/master)*** to add new features: 
* Insert an _All_ category so you can easily **search your entire catalog**.  
* Update ***[Mpv](https://mpv.io/)*** and ***[Sfvip Player](https://github.com/K4L4Uz/SFVIP-Player/tree/master)*** so you can enjoy their latest features. 
* Support an **external EPG**.

<img src="resources/all.png">

# Download
[<img src="https://custom-icon-badges.demolab.com/badge/{name} v{version} x64-informational.svg?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="30"><img src="https://custom-icon-badges.demolab.com/badge/{exe_x64_clean}.svg?logo=shield-check&logoColor=white&style=flat-square" height="30">](https://github.com/{github_path}/raw/master/{exe_x64_link})
<sub><sup>_by Microsoft Defender • {exe_x64_engine} • {exe_x64_signature}_</sup></sub>

[<img src="https://custom-icon-badges.demolab.com/badge/{name} v{version} x86-informational.svg?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="30"><img src="https://custom-icon-badges.demolab.com/badge/{exe_x86_clean}.svg?logo=shield-check&logoColor=white&style=flat-square" height="30">](https://github.com/{github_path}/raw/master/{exe_x86_link})
<sub><sup>_by Microsoft Defender • {exe_x86_engine} • {exe_x86_signature}_</sup></sub>

Check the [***changelog***](build/changelog.md) and ***notes***[^1].  
[***Sfvip Player***](https://github.com/K4L4Uz/SFVIP-Player/tree/master) will be automatically installed if missing.  
Please use [***SfvipUserProxy***](user_proxy_cmd) if you need to add or remove an user proxy for ***all users*** in ***Sfvip Player*** database.

[^1]:_**{name}** will ask you for network connection its first run because it relies on local proxies to do its magic._  
_On **old systems** you might need to install [**vc redist**](https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist) for [**x86**](https://aka.ms/vs/17/release/vc_redist.x86.exe) or [**x64**](https://aka.ms/vs/17/release/vc_redist.x64.exe)._  

# Build
[![Python](https://img.shields.io/badge/Python-{py_version}-fbdf79?logo=python&logoColor=fbdf79)](https://www.python.org/downloads/release/python-{py_version_compact}/)
[![mitmproxy](https://custom-icon-badges.demolab.com/badge/Mitmproxy-{mitmproxy_version}-informational.svg?logo=mitmproxy)](https://mitmproxy.org/)
[![Style](https://custom-icon-badges.demolab.com/badge/Style-Black-000000.svg?logo=file-code&logoColor=a0a0a0)](https://black.readthedocs.io/en/stable/)
![Sloc](https://custom-icon-badges.demolab.com/badge/Sloc-{sloc}-000000.svg?logo=file-code&logoColor=a0a0a0)

[![Nsis](https://img.shields.io/badge/Nsis-{nsis_version}-informational?logo=NSIS&logoColor=fbdf79)](https://nsis.sourceforge.io/Download)
[![Nuitka](https://custom-icon-badges.demolab.com/badge/Nuitka-{nuitka_version}-informational.svg?logo=tools&logoColor=61dafb)](https://nuitka.net/)
<sup><sub>or</sub></sup>
[![PyInstaller](https://custom-icon-badges.demolab.com/badge/PyInstaller-{pyinstaller_version}-informational.svg?logo=tools&logoColor=61dafb)](https://pyinstaller.org/en/stable/)

[***NSIS***](https://nsis.sourceforge.io/Download) will be automatically installed if missing.  
Check the [***build config***](build_config.py).
### Create the environments
You need ***Python {py_major_version}*** [***x64***](https://www.python.org/ftp/python/{py_version}/python-{py_version}-amd64.exe) and [***x86***](https://www.python.org/ftp/python/{py_version}/python-{py_version}.exe) installed to create the environments:
```console
py -{py_major_version}-64 -m dev.create
py -{py_major_version}-32 -m dev.create
```
### Activate the _x64_ environment
```console
{env_x64}\scripts\activate
```
### Run locally
```console
python -m {script_main}
```
### Build with ***PyInstaller***
It's the _fastest option but with more AV false positives:_
```console
python -m dev.build --pyinstaller
```
### Build with ***Nuitka & Mingw***
It's the _easiest option:_
```console
python -m dev.build --mingw
```
### Build with ***Nuitka & Clang***
It's the _recommended option:_
```console
python -m dev.build
```
You need to have [**Visual Studio Community Edition**](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx) with those [**components**](resources/.vsconfig) installed before building:

<img src="resources/VS.png">

### Build an ***x86*** version
You need to [***install Rust***](https://www.rust-lang.org/fr) and `i686-pc-windows-msvc` to build the x86 version of mitmproxy:  
```console
rustup target add i686-pc-windows-msvc
```
### Build a specific version
```console
python -m dev.build [--x86 | --x64 | --both] [--pyinstaller | --mingw] [--nobuild | --noinstaller | --readme] [--upgrade] [--publish]
```
### Upgrade dependencies
It checks for _Nsis_, _Python_ minor update and all _packages dependencies_:
```console
python -m dev.upgrade [--x86 | --x64 | --both] [--noeager] [--clean] [--force]
```
### Publish an update
```console
python -m dev.publish [--x86 | --x64 | --both] [--version VERSION] [--info]
```
### Scan for virus
It updates _Microsoft Defender_ engine and signatures before scanning:
```console
python -m dev.scan [--x86 | --x64 | --both]
```

### Translations
Get a [***DeepL API key***](https://www.deepl.com/en/docs-api/) and set `DEEPL_KEY` in `api_keys.py`:
```python3
# api_keys.py
DEEPL_KEY=your_deepl_api_key
```
Translate the [**UI**](translations/loc/texts.py):
```console
python -m dev.translate [--force] [--language LANGUAGE]
```
