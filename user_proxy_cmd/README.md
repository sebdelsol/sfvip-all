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
[<img src="https://custom-icon-badges.demolab.com/badge/SfvipUserProxy v0.4-informational.svg?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="28"><img src="https://img.shields.io/badge/x64-informational.svg?logo=Windows10&logoColor=lightblue&style=flat-square" height="28"><img src="https://custom-icon-badges.demolab.com/badge/clean-brightgreen.svg?logo=shield-check&logoColor=white&style=flat-square" height="28">](https://github.com/sebdelsol/sfvip-all/releases/download/SfvipUserProxy.0.4/Install.SfvipUserProxy.0.4.x64.exe)
<sup><sup>_by MS Defender • 1.1.24010.10 • 1.405.651.0_</sup></sup>

[<img src="https://custom-icon-badges.demolab.com/badge/SfvipUserProxy v0.4-informational.svg?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="28"><img src="https://img.shields.io/badge/x86-informational.svg?logo=Windows10&logoColor=lightblue&style=flat-square" height="28"><img src="https://custom-icon-badges.demolab.com/badge/clean-brightgreen.svg?logo=shield-check&logoColor=white&style=flat-square" height="28">](https://github.com/sebdelsol/sfvip-all/releases/download/SfvipUserProxy.0.4/Install.SfvipUserProxy.0.4.x86.exe)
<sup><sup>_by MS Defender • 1.1.24010.10 • 1.405.651.0_</sup></sup>

# Build
[![Python](https://img.shields.io/badge/Python-3.11.8-fbdf79?logo=python&logoColor=fbdf79)](https://www.python.org/downloads/release/python-3118/)
[![Style](https://custom-icon-badges.demolab.com/badge/Style-Black-000000.svg?logo=file-code&logoColor=a0a0a0)](https://black.readthedocs.io/en/stable/)
![Sloc](https://custom-icon-badges.demolab.com/badge/Sloc-207-000000.svg?logo=file-code&logoColor=a0a0a0)
[![Nsis](https://img.shields.io/badge/Nsis-3.09-informational?logo=NSIS&logoColor=fbdf79)](https://nsis.sourceforge.io/Download)
[![Nuitka](https://custom-icon-badges.demolab.com/badge/Nuitka-2.0.5-informational.svg?logo=tools&logoColor=61dafb)](https://nuitka.net/)
[![PyInstaller](https://custom-icon-badges.demolab.com/badge/PyInstaller-6.4.0-informational.svg?logo=tools&logoColor=61dafb)](https://pyinstaller.org/en/stable/)


```console
python -m user_proxy_cmd.dev.build [--x86 | --x64 | --both] [--pyinstaller | --mingw] [--nobuild | --noinstaller | --readme] [--publish]
```
### Publish a release
```console
python -m user_proxy_cmd.dev.publish [--x86 | --x64 | --both] [--version VERSION] [--info]
```
### Virus scan
It updates _Microsoft Defender_ engine and signatures before scanning:
```console
python -m user_proxy_cmd.dev.scan [--x86 | --x64 | --both]
```
