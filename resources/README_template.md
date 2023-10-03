# <img src="{ico_link}" width="40" align="center"> {name}
***{name}*** wraps ***[Sfvip Player](https://github.com/K4L4Uz/SFVIP-Player/tree/master)*** with a local proxy that inserts an _All_ category into _Live_, _Series_ and _Vod_.  
So you can easily **search your entire catalog**.

<img src="resources/all.png">

# Download
[<img src="https://img.shields.io/badge/Version-{version}-informational"><img src="https://img.shields.io/badge/x64-informational?logo=windows&logoColor=white"><img src="https://img.shields.io/badge/Exe-informational">](https://github.com/{github_path}/raw/master/{exe64_link}) <sup>or</sup> [<img src="https://img.shields.io/badge/Zip-informational">](https://github.com/{github_path}/raw/master/{archive64_link})

[<img src="https://img.shields.io/badge/Version-{version}-informational"><img src="https://img.shields.io/badge/x86-informational?logo=windows&logoColor=white"><img src="https://img.shields.io/badge/Exe-informational">](https://github.com/{github_path}/raw/master/{exe32_link}) <sup>or</sup> [<img src="https://img.shields.io/badge/Zip-informational">](https://github.com/{github_path}/raw/master/{archive32_link})

Check the [***changelog***](build/changelog.md) and the ***notes***[^1].

Get [***SfvipUserProxy***](user_proxy_cmd) _command line_ to add or remove an user proxy for ***all users*** in ***Sfvip Player*** database.

[^1]:_**{name}** might be slow to start its first run because it unzips in a cached folder._  
_**{name}** might trigger your antivirus because even Nuitka build are not exempt from it._  
_**{name}** will ask you for network connection its first run because it relies on local proxies to do its magic._  
_On **old systems** you might need to install [**vc redist**](https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist) for [**x86**](https://aka.ms/vs/17/release/vc_redist.x86.exe) or [**x64**](https://aka.ms/vs/17/release/vc_redist.x64.exe)._

# Build
[![Python](https://img.shields.io/badge/Python-{py_version}-fbdf79)](https://www.python.org/downloads/release/python-{py_version_compact}/)
[![Nuitka](https://img.shields.io/badge/Nuitka-{nuitka_version}-lightgrey)](https://nuitka.net/)
[![Style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)
![Sloc](https://img.shields.io/badge/Sloc-{sloc}-informational)

Check the [***build config***](build_config.py).
### Create an x64 environment
With [***Python {py_version} x64***](https://www.python.org/ftp/python/{py_version}/python-{py_version}-amd64.exe) or above.  
Set ***{env_x64_decl}*** appropriately if you use a different environement.  
```console
python -m venv {env_x64}
{env_x64}\scripts\activate
python -m pip install -r requirements.txt -r requirements.dev.txt
```
### Run locally
```console
python -m {script_main}
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
You need [**Visual Studio Community Edition**](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx) with those [**components**](resources/.vsconfig):

<img src="resources/VS.png">

### Build an **x86** version
With [***Python {py_version} x86***](https://www.python.org/ftp/python/{py_version}/python-{py_version}.exe) or above.  
Set ***{env_x86_decl}*** appropriately if you use a different environement.  
```console
python -m venv {env_x86}
{env_x86}\scripts\activate
python -m pip install -r requirements.txt -r requirements.dev.txt -r requirements.x86.txt
```
You need to [***install Rust***](https://www.rust-lang.org/fr) and `i686-pc-windows-msvc` to build the ***x86*** version of mitmproxy:  
```console
rustup target add i686-pc-windows-msvc
```
### Build a specific version
```console
python -m build [--x86 | --x64 | --both] [--nobuild | --noexe | --nozip] [--mingw] [--upgrade] [--publish]
```
### Upgrade dependencies
```console
python -m upgrade [--x86 | --x64 | --both] [--noeager]
```
### Publish an update
```console
python -m publish [--x86 | --x64 | --both] [--version VERSION] [--info]
```

### Translate the UI
```console
python -m translate [--force-update]
```
