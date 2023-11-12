# <img src="resources/Sfvip%20All.png" width="40" align="center"> Sfvip All
***Sfvip All*** wraps ***[Sfvip Player](https://github.com/K4L4Uz/SFVIP-Player/tree/master)*** with a local proxy that inserts an _All_ category into _Live_, _Series_ and _Vod_.  
So you can easily **search your entire catalog**. It also **updates [mpv player](https://mpv.io/)** dll so you can enjoy its lastest features.

<img src="resources/all.png">

# Download
[<img src="https://img.shields.io/badge/Version-1.4.2-informational"><img src="https://img.shields.io/badge/x64-informational?logo=windows&logoColor=white"><img src="https://img.shields.io/badge/installer-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.4.2/x64/Install%20Sfvip%20All.exe)

[<img src="https://img.shields.io/badge/Version-1.4.2-informational"><img src="https://img.shields.io/badge/x86-informational?logo=windows&logoColor=white"><img src="https://img.shields.io/badge/installer-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.4.2/x86/Install%20Sfvip%20All.exe)

Check the [***changelog***](build/changelog.md) and ***notes***[^1].  
Get [***SfvipUserProxy***](user_proxy_cmd) _command line_ to add or remove an user proxy for ***all users*** in ***Sfvip Player*** database.

[^1]:_**Sfvip All** will ask you for network connection its first run because it relies on local proxies to do its magic._  
_On **old systems** you might need to install [**vc redist**](https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist) for [**x86**](https://aka.ms/vs/17/release/vc_redist.x86.exe) or [**x64**](https://aka.ms/vs/17/release/vc_redist.x64.exe)._

# Build
[![Python](https://img.shields.io/badge/Python-3.11.6-fbdf79)](https://www.python.org/downloads/release/python-3116/)
[![Nuitka](https://img.shields.io/badge/Nuitka-1.8.6-informational)](https://nuitka.net/)
[![Nsis](https://img.shields.io/badge/Nsis-3.09-informational)](https://nsis.sourceforge.io/Download)
[![Style](https://img.shields.io/badge/Style-Black-000000)](https://black.readthedocs.io/en/stable/)
![Sloc](https://img.shields.io/badge/Sloc-4885-informational)

Check the [***build config***](build_config.py).  
You need [***NSIS***](https://nsis.sourceforge.io/Download) to create the installer.
### Create an x64 environment
With [***Python 3.11.6 x64***](https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe) or above.  
Set ***[`Environments.X64.path`](/build_config.py#L34)*** appropriately if you use a different environement.  
```console
python -m venv .sfvip64
.sfvip64\scripts\activate
python -m pip install -r requirements.txt -r requirements.dev.txt
```
### Run locally
```console
python -m sfvip_all
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

### Build an **x86** version
With [***Python 3.11.6 x86***](https://www.python.org/ftp/python/3.11.6/python-3.11.6.exe) or above.  
Set ***[`Environments.X86.path`](/build_config.py#L38)*** appropriately if you use a different environement.  
```console
python -m venv .sfvip86
.sfvip86\scripts\activate
python -m pip install -r requirements.txt -r requirements.dev.txt -c constraints.x86.txt
```
You need to [***install Rust***](https://www.rust-lang.org/fr) and `i686-pc-windows-msvc` to build the x86 version of [***mitmproxy***](https://mitmproxy.org/):  
```console
rustup target add i686-pc-windows-msvc
```
### Build a specific version
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
