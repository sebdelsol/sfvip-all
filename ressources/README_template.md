# <img src="{ico_link}" width="40" align="center"> {name}
***{name}*** wraps ***[Sfvip Player](https://serbianforum-org.translate.goog/threads/sf-vip-plejer.878393/?_x_tr_sl=sr&_x_tr_tl=en)*** with a proxy that inserts an _{all}_ category into {inject}.  
So you can easily **search your entire catalog**.

<img src="ressources/all.png">

## Download the [**Exe**](https://github.com/{github_path}/raw/master/{exe_link}) or [**Zip**](https://github.com/{github_path}/raw/master/{archive_link})
[![Version](https://img.shields.io/badge/Version-{version}-informational)](https://github.com/{github_path}/raw/master/{exe_link})
[![Windows](https://img.shields.io/badge/Windows-x64-white)](https://www.microsoft.com/windows/)
[![dist](https://img.shields.io/badge/Dist-Nuitka-fbdf79)](https://nuitka.net/)  
<sub>_Launch **Sfvip Player** at least once before so **Sfvip All** could automatically find the player._</sub>  
<sub>_The standalone **Sfvip All.exe** might be a little slow to start its first run._</sub>
## Build
[![Python](https://img.shields.io/badge/Python-3.11-fbdf79)](https://www.python.org/downloads/release/python-3113/)
[![style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)
![sloc](https://tokei.rs/b1/github/{github_path}?category=lines)  
_Check [**build config**](build_config.py)._
### Create an environment
```console
python -m venv .sfvip
.sfvip\scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements.dev.txt
```
### Run locally
```console
python -m sfvip_all
```
### Build with ***Mingw64*** <sub><sup>the easiest option</sup></sub>
```console
python -m build
```
### Or build with ***Clang*** <sub><sup>the recommended option</sup></sub>
```console
python -m build --clang
```
You'll need [**Visual Studio Community Edition**](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx) with those [**components**](ressources/.vsconfig):

<img src="ressources/VS.png">