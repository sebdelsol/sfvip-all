# <img src="ressources/Sfvip%20All.png" width="40" align="center"> Sfvip All

***Sfvip All*** wraps ***[Sfvip Player](https://serbianforum-org.translate.goog/threads/sf-vip-plejer.878393/?_x_tr_sl=sr&_x_tr_tl=en)*** with a proxy that inserts an _All_ category into _Series_ and _Vod_.  
So you can easily **search your entire catalog**.

<img src="ressources/all.PNG" width="350">

## Download
[![Version](https://img.shields.io/badge/Version-1.1.3-informational)](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.1.3/Sfvip%20All.exe)
[![Windows](https://img.shields.io/badge/Windows-x64-white)](https://www.microsoft.com/windows/)

Download the [**Exe**](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.1.3/Sfvip%20All.exe)
or [**Zip**](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.1.3/Sfvip%20All.zip).  
<sub>_You must have launched **Sfvip Player** at least once before._</sub>  
<sub>_The standalone **Exe** might be a little slow to start since it unzips its Python environment._</sub>
## Build
[![Python](https://img.shields.io/badge/Python-3.11-fbdf79)](https://www.python.org/downloads/release/python-3113/)
[![style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)
[![dist](https://img.shields.io/badge/Dist-Nuitka-lightgrey)](https://nuitka.net/)
![sloc](https://tokei.rs/b1/github/sebdelsol/sfvip-all?category=code)

Create the environment:
```console
python -m venv .sfvip
.sfvip\scripts\activate
pip install -r requirements.txt
pip install -r requirements.dev.txt
```
Check the [**build config**](build_config.py) and build:
```console
python -m build
```