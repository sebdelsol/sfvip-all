# <img src="{ico_link}" width="40" align="center"> {name}

***{name}*** wraps ***[Sfvip Player](https://serbianforum-org.translate.goog/threads/sf-vip-plejer.878393/?_x_tr_sl=sr&_x_tr_tl=en)*** with a proxy that inserts an _{all}_ category into {inject}.  
So you can easily **search your entire catalog**.

<img src="ressources/all.png">

## Download and Run
[![Version](https://img.shields.io/badge/Version-{version}-informational)](https://github.com/{github_path}/raw/master/{exe_link})
[![Windows](https://img.shields.io/badge/Windows-x64-white)](https://www.microsoft.com/windows/)

Download the [**Exe**](https://github.com/{github_path}/raw/master/{exe_link})
or [**Zip**](https://github.com/{github_path}/raw/master/{archive_link}).  
<sub>_You must have launched **Sfvip Player** at least once before._</sub>  
<sub>_The standalone **Exe** might be a little slow to start at first._</sub>
## Build
[![Python](https://img.shields.io/badge/Python-3.11-fbdf79)](https://www.python.org/downloads/release/python-3113/)
[![style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)
[![dist](https://img.shields.io/badge/Dist-Nuitka-lightgrey)](https://nuitka.net/)
![sloc](https://tokei.rs/b1/github/{github_path}?category=code)

Check [**build config**](build_config.py) and create the environment:
```console
python -m venv .sfvip
.sfvip\scripts\activate
pip install -r requirements.txt
pip install -r requirements.dev.txt
```
### Build with ***Mingw64*** <sub><sup>the easiest option</sup></sub>
```console
python -m build
```
### Build with ***Clang*** <sub><sup>the recommended option</sup></sub>
```console
python -m build --clang
```
You need [**Visual Studio Community Edition**](https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx) with those [**components**](ressources/.vsconfig):

<img src="ressources/VS.png">  

### Update only ***readme***
```console
python -m build --nobuild
```
