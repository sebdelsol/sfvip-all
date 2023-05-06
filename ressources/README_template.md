# <img src="{ico_link}" width="40" align="center"> {name}
[![Version](https://img.shields.io/badge/Version-{version}-informational)](https://github.com/{github_path}/raw/master/{archive_link})

**{name}** wraps **Sfvip Player** with a proxy that inserts an "All" category into _Vod_ and _Series_.  
**So you can easily browse the entire catalog**.

<img src="ressources/all.PNG" width="350">

## Run
[![Windows](https://img.shields.io/badge/Windows-x64-white)](https://www.microsoft.com/windows/)
- Download it [**from here**](https://github.com/{github_path}/raw/master/{archive_link}) & unzip[^1].
- Launch **`{name}.exe`**[^2].

## Build
[![Python](https://img.shields.io/badge/Python-3.11-fbdf79)](https://www.python.org/downloads/release/python-3113/)
- `python -m venv .sfvip`
- `.sfvip\scripts\activate`
- `pip install -r requirements.txt`
- `pip install -r requirements.dev.txt`
- Check [build_config.py](https://github.com/{github_path}/blob/master/build_config.py).
- `python -m build`

[^1]: _The archive might be removed by MS defender due to this [bug](https://github.com/pyinstaller/pyinstaller/issues/5854)._
[^2]: _You must have launched **Sfvip Player** at least once before_