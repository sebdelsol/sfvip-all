# <img src="ressources/Sfvip%20All.png" width="40" align="center"> Sfvip All
***Sfvip All*** wraps ***[Sfvip Player](https://serbianforum-org.translate.goog/threads/sf-vip-plejer.878393/?_x_tr_sl=sr&_x_tr_tl=en)*** with a local proxy that inserts an _All_ category into _Live_, _Series_ and _Vod_.  
So you can easily **search your entire catalog**.

<img src="ressources/all.png">

# Download
<img src="https://img.shields.io/badge/Version-1.2.0-informational" valign="middle"><img src="https://img.shields.io/badge/x64-informational?logo=windows&logoColor=white" valign="middle"> &nbsp;[***Executable***](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.2.0/x64/Sfvip%20All.exe) or [zip](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.2.0/x64/Sfvip%20All.zip).

<img src="https://img.shields.io/badge/Version-1.2.0-informational" valign="middle"><img src="https://img.shields.io/badge/x86-informational?logo=windows&logoColor=white" valign="middle"> &nbsp;[***Executable***](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.2.0/x86/Sfvip%20All.exe) or [zip](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.2.0/x86/Sfvip%20All.zip).

You need to have ***[Sfvip Player](https://serbianforum-org.translate.goog/threads/sf-vip-plejer.878393/?_x_tr_sl=sr&_x_tr_tl=en)*** last version already installed <sub><sup>_and preferably launched at least once._</sup></sub>  
<sub>_**Sfvip All.exe** might be slow to start its first run because it unzips in a cached folder._</sub>  
<sub>_**Sfvip All.exe** might trigger your antivirus because even Nuitka build are not exempt from it._</sub>  
<sub>_**Sfvip All.exe** will ask you for network connection its first run because it relies on local proxies to do its magic._</sub>  
<sub>_On **old systems** you might need to install [**vc redist**](https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist) for [**x86**](https://aka.ms/vs/17/release/vc_redist.x86.exe) or [**x64**](https://aka.ms/vs/17/release/vc_redist.x64.exe)._</sub>

Check the [***changelog***](build/changelog.md).

# Build
[![Python](https://img.shields.io/badge/Python-3.11.4-fbdf79)](https://www.python.org/downloads/release/python-3114/)
[![dist](https://img.shields.io/badge/Dist-Nuitka-lightgrey)](https://nuitka.net/)
[![style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)
![sloc](https://img.shields.io/badge/Sloc-2388-informational)

Check the [***build config***](build_config.py).
### Create an environment
```console
python -m venv .sfvip
.sfvip\scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements.dev.txt
```
Everything that follows should be done in the ***.sfvip environment***.
### Upgrade dependencies
```console
python -m upgrade
```
### Run locally
```console
python -m sfvip_all
```
### Build with ***Mingw64*** <sub><sup>the easiest option</sup></sub>
```console
python -m build --mingw
```
### Build with ***Clang*** <sub><sup>the recommended option</sup></sub>
```console
python -m build
```
You need [**Visual Studio Community Edition**](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx) with those [**components**](ressources/.vsconfig):

<img src="ressources/VS.png">

### Build an ***x86*** version
Create another [***environment***](#Create-the-environment) with a ***32bit Python*** version:  
It should be called ***.sfvip32*** or you have to set [***`Environments.x86`***](build_config.py#L12) appropriately.  
You need to [***install Rust***](https://www.rust-lang.org/fr) and `i686-pc-windows-msvc` to build the x86 version of mitmproxy.  
```console
rustup target add i686-pc-windows-msvc
```
### Build a specific version:
```console
python -m build [--x86 | --x64 | --both]
```
