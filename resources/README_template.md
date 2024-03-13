# <kbd><img src="{ico_link}" width="45"></kbd> {name}
***{name}*** wraps ***[Sfvip Player](https://github.com/K4L4Uz/SFVIP-Player/tree/master)*** to add new features: 
* Insert an _All_ category when missing so you can easily **search your entire catalog**.  
<kbd><img src="resources/readme/all.png"></kbd>
* Update ***[Mpv](https://mpv.io/)*** and ***[Sfvip Player](https://github.com/K4L4Uz/SFVIP-Player/tree/master)*** so you can enjoy their latest features. 
* Support an **external EPG**[^1].

[^1]: External EPG doesn't work with **local** m3u accounts.
# Downloads
[<img src="https://custom-icon-badges.demolab.com/badge/{name} v{version_x64}-informational?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="{h_download}"><img src="https://img.shields.io/badge/x64-informational?logo=Windows10&logoColor=lightblue&style=flat-square" height="{h_download}"><img src="https://custom-icon-badges.demolab.com/badge/{exe_x64_clean}?logo=shield-check&logoColor=white&style=flat-square" height="{h_download}">]({exe_x64_release})
<sup><sup>_by MS Defender • {exe_x64_engine} • {exe_x64_signature}_</sup></sup>

[<img src="https://custom-icon-badges.demolab.com/badge/{name} v{version_x86}-informational?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="{h_download}"><img src="https://img.shields.io/badge/x86-informational?logo=Windows10&logoColor=lightblue&style=flat-square" height="{h_download}"><img src="https://custom-icon-badges.demolab.com/badge/{exe_x86_clean}?logo=shield-check&logoColor=white&style=flat-square" height="{h_download}">]({exe_x86_release})
<sup><sup>_by MS Defender • {exe_x86_engine} • {exe_x86_signature}_</sup></sup>

[<a href="https://tooomm.github.io/github-release-stats/?username={github_owner}&repository={github_repo}"><img src="https://img.shields.io/github/downloads/{github_path}/total?color=informational&logo=github&labelColor=informational&style=flat-square" height="{h_github}"></a><a href="https://github.com/{github_path}/issues?q=is%3Aopen"><img src="https://img.shields.io/github/issues/{github_path}?labelColor=success&style=flat-square" height="{h_github}"></a>]()

* Check the [***changelog***](build/changelog.md) and ***notes***[^2].  
* [***Sfvip Player***](https://github.com/K4L4Uz/SFVIP-Player/tree/master) will be automatically installed if missing.  
* Please use [***SfvipUserProxy***](user_proxy_cmd) to add or remove a proxy for ***all users*** in ***Sfvip Player*** database.

[^2]:_**{name}** will ask for network connection its first run because it relies on local proxies to do its magic._  
_On **old systems** you might need to install [**vc redist**](https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist) for [**x86**](https://aka.ms/vs/17/release/vc_redist.x86.exe) or [**x64**](https://aka.ms/vs/17/release/vc_redist.x64.exe)._  

# Settings
* Hover your mouse over the ***{name}*** logo:  
  <kbd><img src="resources/readme/logo_arrow.png"></kbd>  

* To open the settings:  
  <kbd><img src="resources/readme/settings.png"></kbd>  

* Logo pulse meaning:  
  Color & pulse | Meaning
  :--- | :---
  <kbd><img src="resources/readme/logo_green.png" width="25"></kbd> <sub>slow pulse | <sub>Everything is fine
  <kbd><img src="resources/readme/logo_red.png" width="25"></kbd>  <sub>quick pulse | <sub>_{name}_ needs your attention

# Logs
The logs go **in pairs** (one for each process: ***main*** & ***mitmproxy***) and they are in the app folder:

<kbd><img src="resources/readme/logs.png"></kbd>  

# Build
[![version](https://custom-icon-badges.demolab.com/badge/Build%20{build_version}-informational?logo=github)]({build_version_link})
[![Sloc](https://custom-icon-badges.demolab.com/badge/Sloc%20{sloc}-informational?logo=file-code)](https://api.codetabs.com/v1/loc/?github={github_path})
[![Ruff](https://custom-icon-badges.demolab.com/badge/Ruff-informational?logo=ruff-color)](https://docs.astral.sh/ruff/)
[![Python](https://custom-icon-badges.demolab.com/badge/Python%20{py_version}-linen?logo=python-color)](https://www.python.org/downloads/release/python-{py_version_compact}/)
[![mitmproxy](https://custom-icon-badges.demolab.com/badge/Mitmproxy%20{mitmproxy_version}-linen?logo=mitmproxy-black)](https://mitmproxy.org/)
[![Nsis](https://custom-icon-badges.demolab.com/badge/Nsis%20{nsis_version}-linen?logo=nsis-color)](https://nsis.sourceforge.io/Download)
[![Nuitka](https://custom-icon-badges.demolab.com/badge/Nuitka%20{nuitka_version}-linen?logo=nuitka)](https://nuitka.net/)
[![PyInstaller](https://custom-icon-badges.demolab.com/badge/PyInstaller%20{pyinstaller_version}-linen?logo=pyinstaller-windowed)](https://pyinstaller.org/en/stable/)

* [***NSIS***](https://nsis.sourceforge.io/Download) will be automatically installed if missing.  
* Check the [***build config***](build_config.py).

### Create the environments
You need [***Rust***](https://www.rust-lang.org/fr), [***Python {py_major_version} x64***](https://www.python.org/ftp/python/{py_version}/python-{py_version}-amd64.exe) & [***x86***](https://www.python.org/ftp/python/{py_version}/python-{py_version}.exe):
```console
rustup target add i686-pc-windows-msvc
py -{py_major_version}-64 -m dev.create
py -{py_major_version}-32 -m dev.create
```
Get a [***Github token***](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#personal-access-tokens-classic) & a [***DeepL API key***](https://www.deepl.com/en/docs-api/) and store those in `api_keys.py`:
```python3
# api_keys.py
GITHUB_TOKEN=your_github_token
DEEPL_KEY=your_deepl_api_key
```

### Activate an environment
The [x64 environment]({x64_env_link}):
```console
{env_x64}\scripts\activate
```
Or the [x86 environment]({x86_env_link}):
```console
{env_x86}\scripts\activate
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
You need [**Visual Studio**](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx) with those [**components**](resources/readme/.vsconfig):

<kbd><img src="resources/readme/VS.png"></kbd>

### Build a specific version
```console
python -m dev.build [--x86 | --x64 | --both] [--pyinstaller | --mingw] [--nobuild | --noinstaller | --readme] [--upgrade] [--publish]
```
### Upgrade dependencies
It checks for _Nsis_, _Python minor update_ and all _packages dependencies_:
```console
python -m dev.upgrade [--x86 | --x64 | --both] [--noeager] [--clean] [--force]
```
### Virus scan
It updates _Microsoft Defender_ engine and signatures before scanning:
```console
python -m dev.scan [--x86 | --x64 | --both]
```
### Translate the [**UI**](translations/loc/texts.py)
```console
python -m dev.translate [--force] [--language LANGUAGE]
```
### Publish a release
```console
python -m dev.publish [--x86 | --x64 | --both] [--version VERSION] [--info]
```
### Nuitka vs. Pyinstaller
| | _Nuitka_  | _Pyinstaller_|
| :- | :- | :- |
| _AV false positives_ | <sub>✅ lower| <sub>❌ higher |
| _Run time speed_ | <sub>✅ faster | <sub>❌ slower |
| _Distribution size_ | <sub>❌ bigger  | <sub>✅ smaller |
| _Build time_ | <sub>❌ slower| <sub>✅ faster|
