# <img src="ressources/Sfvip%20All.png" width="40" align="center"> Sfvip All
***Sfvip All*** wraps ***[Sfvip Player](https://github.com/K4L4Uz/SFVIP-Player/tree/master)*** with a local proxy that inserts an _All_ category into _Live_, _Series_ and _Vod_.  
So you can easily **search your entire catalog**.

<img src="ressources/all.png">

# Download
[<img src="https://img.shields.io/badge/Version-1.2.9-informational"><img src="https://img.shields.io/badge/x64-informational?logo=windows&logoColor=white"><img src="https://img.shields.io/badge/Exe-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.2.9/x64/Sfvip%20All.exe) <sup>or</sup> [<img src="https://img.shields.io/badge/Zip-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.2.9/x64/Sfvip%20All.zip)

[<img src="https://img.shields.io/badge/Version-1.2.9-informational"><img src="https://img.shields.io/badge/x86-informational?logo=windows&logoColor=white"><img src="https://img.shields.io/badge/Exe-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.2.9/x86/Sfvip%20All.exe) <sup>or</sup> [<img src="https://img.shields.io/badge/Zip-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.2.9/x86/Sfvip%20All.zip)

Check the [***changelog***](build/changelog.md) and the ***notes***[^1].

Get [***SfvipUserProxy***](user_proxy_cmd) _command line_ to add or remove an user proxy for ***all users*** in ***Sfvip Player*** database.

[^1]:_**Sfvip All** might be slow to start its first run because it unzips in a cached folder._  
_**Sfvip All** might trigger your antivirus because even Nuitka build are not exempt from it._  
_**Sfvip All** will ask you for network connection its first run because it relies on local proxies to do its magic._  
_On **old systems** you might need to install [**vc redist**](https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist) for [**x86**](https://aka.ms/vs/17/release/vc_redist.x86.exe) or [**x64**](https://aka.ms/vs/17/release/vc_redist.x64.exe)._

# Build
[![Python](https://img.shields.io/badge/Python-3.11.5-fbdf79)](https://www.python.org/downloads/release/python-3115/)
[![Nuitka](https://img.shields.io/badge/Nuitka-1.8.2-lightgrey)](https://nuitka.net/)
[![Style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)
![Sloc](https://img.shields.io/badge/Sloc-3372-informational)

Check the [***build config***](build_config.py).
### Create an x64 environment
Create a [***Python x64***](https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe) ***environment***.  
Call it ***.sfvip64*** or you have to set ***[`Environments.X64.path`](/build_config.py#L28)*** appropriately.
```console
python -m venv .sfvip64
.sfvip64\scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements.dev.txt
```

### Run locally
```console
python -m sfvip_all
```
### Build with ***Mingw64***
_The easiest option._
```console
python -m build --mingw
```
### Build with ***Clang***
_The recommended option._
```console
python -m build
```
You need [**Visual Studio Community Edition**](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx) with those [**components**](ressources/.vsconfig):

<img src="ressources/VS.png">

### Build an ***x86*** version
Create a [***Python x86***](https://www.python.org/ftp/python/3.11.5/python-3.11.5.exe) [***environment***](#Create-an-x64-environment).  
Call it ***.sfvip86*** or you have to set ***[`Environments.X86.path`](/build_config.py#L32)*** appropriately.  
You need to [***install Rust***](https://www.rust-lang.org/fr) and `i686-pc-windows-msvc` to build the x86 version of mitmproxy:  
```console
rustup target add i686-pc-windows-msvc
```
### Build a specific version
```console
python -m build [--x86 | --x64 | --both] [--nobuild | --noexe | --nozip] [--mingw] [--upgrade]
```
### Upgrade dependencies
```console
python -m upgrade [--x86 | --x64 | --both] [--noeager]
```
