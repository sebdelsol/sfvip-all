# <img src="ressources/Sfvip%20All.png" width="40" align="center"> Sfvip All
***Sfvip All*** wraps ***[Sfvip Player](https://serbianforum-org.translate.goog/threads/sf-vip-plejer.878393/?_x_tr_sl=sr&_x_tr_tl=en)*** with a proxy that inserts an _All_ category into _Live_, _Series_ and _Vod_.  
So you can easily **search your entire catalog**.

<img src="ressources/all.png">

## Download the [**Exe**](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.1.8/Sfvip%20All.exe) or [**Zip**](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.1.8/Sfvip%20All.zip)
[![Version](https://img.shields.io/badge/Version-1.1.8-informational)](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.1.8/Sfvip%20All.exe)
[![Windows](https://img.shields.io/badge/Windows-x64-white)](https://www.microsoft.com/windows/)
[![dist](https://img.shields.io/badge/Dist-Nuitka-fbdf79)](https://nuitka.net/)

You need to have ***[Sfvip Player](https://serbianforum-org.translate.goog/threads/sf-vip-plejer.878393/?_x_tr_sl=sr&_x_tr_tl=en)*** already installed <sub><sup>_and preferably launched at least once._</sup></sub>  
<sub>_**Sfvip All.exe** might be slow to start its first run because it unzips in a cached folder._</sub>  
<sub>_**Sfvip All.exe** might trigger your antivirus because even Nuitka build are not exempt from it._</sub>  
<sub>_**Sfvip All.exe** will ask you for network connection its first run because it relies on local proxies to do its magic._</sub>

**Check the [_Changelog_](build/changelog.md).**
## Build
[![Python](https://img.shields.io/badge/Python-3.11.4-fbdf79)](https://www.python.org/downloads/release/python-3114/)
[![style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)
![sloc](https://img.shields.io/badge/Loc-2155-informational)

**Check the [_build config_](build_config.py).**
### Create the environment
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
python -m build
```
### Build with ***Clang*** <sub><sup>the recommended option</sup></sub>
```console
python -m build --clang
```
You'll need [**Visual Studio Community Edition**](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx) with those [**components**](ressources/.vsconfig):

<img src="ressources/VS.png">