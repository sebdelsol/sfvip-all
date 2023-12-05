# <img src="resources/Sfvip%20All.png" width="40" align="center"> Sfvip All
***Sfvip All*** wraps ***[Sfvip Player](https://github.com/K4L4Uz/SFVIP-Player/tree/master)*** with a local proxy that inserts an _All_ category into _Live_, _Series_ and _Vod_.  
So you can easily **search your entire catalog**. It also **updates [mpv player](https://mpv.io/)** dll so you can enjoy its lastest features.

<img src="resources/all.png">

# Download
[<img src="https://img.shields.io/badge/Sfvip All 1.4.7 x64-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://img.shields.io/badge/Clean-brightgreen?style=flat-square" height="30">](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.4.7/x64/Install%20Sfvip%20All.exe)<img src="https://custom-icon-badges.demolab.com/badge/Scanned by Microsoft Defender • 1.1.23100.2009 • 1.401.1671.0-white.svg?logo=shield-check&logoColor=black&style=flat-square" height="15">

[<img src="https://img.shields.io/badge/Sfvip All 1.4.7 x86-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://img.shields.io/badge/Clean-brightgreen?style=flat-square" height="30">](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.4.7/x86/Install%20Sfvip%20All.exe)<img src="https://custom-icon-badges.demolab.com/badge/Scanned by Microsoft Defender • 1.1.23100.2009 • 1.401.1671.0-white.svg?logo=shield-check&logoColor=black&style=flat-square" height="15">

Check the [***changelog***](build/changelog.md) and ***notes***[^1].  
Get [***SfvipUserProxy***](user_proxy_cmd) _command line_ to add or remove an user proxy for ***all users*** in ***Sfvip Player*** database.

[^1]:_**Sfvip All** will ask you for network connection its first run because it relies on local proxies to do its magic._  
_On **old systems** you might need to install [**vc redist**](https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist) for [**x86**](https://aka.ms/vs/17/release/vc_redist.x86.exe) or [**x64**](https://aka.ms/vs/17/release/vc_redist.x64.exe)._  

# Build
[![Python](https://img.shields.io/badge/Python-3.11.7-fbdf79?logo=python&logoColor=fbdf79)](https://www.python.org/downloads/release/python-3117/)
[![Nuitka](https://img.shields.io/badge/Nuitka-1.9.3-informational)](https://nuitka.net/)
[![Nsis](https://img.shields.io/badge/Nsis-3.09-informational)](https://nsis.sourceforge.io/Download)
[![mitmproxy](https://img.shields.io/badge/Mitmproxy-10.1.5-informational)](https://mitmproxy.org/)
[![Style](https://img.shields.io/badge/Style-Black-000000)](https://black.readthedocs.io/en/stable/)
![Sloc](https://img.shields.io/badge/Sloc-5227-000000)

[***NSIS***](https://nsis.sourceforge.io/Download) will be automatically installed if missing.  
Check the [***build config***](build_config.py).
### Create the environments
You need ***Python 3.11*** [***x64***](https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe) and [***x86***](https://www.python.org/ftp/python/3.11.7/python-3.11.7.exe) installed to create the environments:
```console
py -3.11-64 -m dev.create_env
py -3.11-32 -m dev.create_env
```
### Activate the _x64_ environment
```console
.sfvip64\scripts\activate
```
### Run locally
```console
python -m sfvip_all
```
### Build with **Mingw**
It's the _easiest option:_
```console
python -m dev.build --mingw
```
### Build with **Clang**
It's the _recommended option:_
```console
python -m dev.build
```
You need to have [**Visual Studio Community Edition**](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx) with those [**components**](resources/.vsconfig) installed before building:

<img src="resources/VS.png">

### Build a specific version
```console
python -m dev.build [--x86 | --x64 | --both] [--nobuild | --noinstaller | --readme] [--upgrade] [--publish] [--mingw]
```
### Upgrade dependencies
It checks for _Nsis_, _Python_ minor update and all _packages dependencies_:
```console
python -m dev.upgrade [--x86 | --x64 | --both] [--noeager] [--clean]
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
