# <img src="ressources/Sfvip%20All.png" width="40" align="center"> Sfvip All
[![Version](https://img.shields.io/badge/Version-1.1.2-informational)](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.1.2/Sfvip%20All.exe)

***Sfvip All*** wraps ***Sfvip Player*** with a proxy that inserts an "All" category into _Vod_ and _Series_.  
So you can easily **search your entire catalog**.

<img src="ressources/all.PNG" width="350">

## Run
[![Windows](https://img.shields.io/badge/Windows-x64-white)](https://www.microsoft.com/windows/)

Download the [**Exe**](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.1.2/Sfvip%20All.exe)
_or_ [**Zip**](https://github.com/sebdelsol/sfvip-all/raw/master/build/1.1.2/Sfvip%20All.zip).  
<sub>_You must have launched **Sfvip Player** at least once before._</sub>  
<sub>_The standalone **Exe** might be a little slow to start since it uncompresses all embedded Python's dependencies._</sub>
## Build
[![Python](https://img.shields.io/badge/Python-3.11-fbdf79)](https://www.python.org/downloads/release/python-3113/)
[![Code style](https://img.shields.io/badge/Code%20Style-Black-000000)](https://github.com/psf/black)

Check [build_config.py](https://github.com/sebdelsol/sfvip-all/blob/master/build_config.py),
create the environment and build:
```console
python -m venv .sfvip
.sfvip\scripts\activate
pip install -r requirements.txt
pip install -r requirements.dev.txt
python -m build
```
