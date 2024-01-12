# SfvipUserProxy
_Command to add an user proxy for **all users** in [**Sfvip Player**](https://github.com/K4L4Uz/SFVIP-Player/tree/master) **database**:_
```console
SfvipUserProxy http://127.0.0.1:8888
```
_Remove it:_
```console
SfvipUserProxy --remove
```

# Download
[<img src="https://custom-icon-badges.demolab.com/badge/SfvipUserProxy v0.4 x64-informational.svg?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="30"><img src="https://custom-icon-badges.demolab.com/badge/clean-brightgreen.svg?logo=shield-check&logoColor=white&style=flat-square" height="30">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.4/x64/Install%20SfvipUserProxy.exe)
<sub><sup>_by Microsoft Defender • 1.1.23110.2 • 1.403.535.0_</sup></sub>

[<img src="https://custom-icon-badges.demolab.com/badge/SfvipUserProxy v0.4 x86-informational.svg?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="30"><img src="https://custom-icon-badges.demolab.com/badge/clean-brightgreen.svg?logo=shield-check&logoColor=white&style=flat-square" height="30">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.4/x86/Install%20SfvipUserProxy.exe)
<sub><sup>_by Microsoft Defender • 1.1.23110.2 • 1.403.535.0_</sup></sub>

# Build
[![Python](https://img.shields.io/badge/Python-3.11.7-fbdf79?logo=python&logoColor=fbdf79)](https://www.python.org/downloads/release/python-3117/)
[![Style](https://custom-icon-badges.demolab.com/badge/Style-Black-000000.svg?logo=file-code&logoColor=a0a0a0)](https://black.readthedocs.io/en/stable/)
![Sloc](https://custom-icon-badges.demolab.com/badge/Sloc-196-000000.svg?logo=file-code&logoColor=a0a0a0)

[![Nuitka](https://custom-icon-badges.demolab.com/badge/Nuitka-1.9.7-informational.svg?logo=tools&logoColor=61dafb)](https://nuitka.net/)
<sup><sub>**or**</sub></sup>
[![PyInstaller](https://custom-icon-badges.demolab.com/badge/PyInstaller-6.3.0-informational.svg?logo=tools&logoColor=61dafb)](https://pyinstaller.org/en/stable/)
<sup><sub>&ensp; **+** &ensp;</sub></sup>
[![Nsis](https://img.shields.io/badge/Nsis-3.09-informational?logo=NSIS&logoColor=fbdf79)](https://nsis.sourceforge.io/Download)

```console
python -m user_proxy_cmd.dev.build [--x86 | --x64 | --both] [--pyinstaller | --mingw] [--nobuild | --noinstaller | --readme]
```