# SfvipUserProxy
_Add an user proxy for **all users** in [**Sfvip Player**](https://github.com/K4L4Uz/SFVIP-Player/tree/master) **database**:_
```console
SfvipUserProxy http://127.0.0.1:8888
```
_Remove it:_
```console
SfvipUserProxy --remove
```

# Downloads
[<img src="https://custom-icon-badges.demolab.com/badge/SfvipUserProxy v0.4-informational?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="35"><img src="https://img.shields.io/badge/x64-informational?logo=Windows10&logoColor=lightblue&style=flat-square" height="35"><img src="https://custom-icon-badges.demolab.com/badge/clean-brightgreen?logo=shield-check&logoColor=white&style=flat-square" height="35">](https://github.com/sebdelsol/sfvip-all/releases/download/SfvipUserProxy.0.4/Install.SfvipUserProxy.0.4.x64.exe)
<sup><sup>_by MS Defender • 1.1.24010.10 • 1.405.651.0_</sup></sup>

[<img src="https://custom-icon-badges.demolab.com/badge/SfvipUserProxy v0.4-informational?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="35"><img src="https://img.shields.io/badge/x86-informational?logo=Windows10&logoColor=lightblue&style=flat-square" height="35"><img src="https://custom-icon-badges.demolab.com/badge/clean-brightgreen?logo=shield-check&logoColor=white&style=flat-square" height="35">](https://github.com/sebdelsol/sfvip-all/releases/download/SfvipUserProxy.0.4/Install.SfvipUserProxy.0.4.x86.exe)
<sup><sup>_by MS Defender • 1.1.24010.10 • 1.405.651.0_</sup></sup>

# Build
[![version](https://custom-icon-badges.demolab.com/badge/Build%200.4-informational?logo=github)](/user_proxy_cmd/cmd_build_config.py#L12)
[![Sloc](https://custom-icon-badges.demolab.com/badge/Sloc%20207-informational?logo=file-code)](https://api.codetabs.com/v1/loc/?github=sebdelsol/sfvip-all)
[![Ruff](https://custom-icon-badges.demolab.com/badge/Ruff-informational?logo=ruff-color)](https://docs.astral.sh/ruff/)
<sup><sub>with</sup></sub>
[![Python](https://custom-icon-badges.demolab.com/badge/Python%203.11.8-linen?logo=python-color)](https://www.python.org/downloads/release/python-3118/)
[![Nsis](https://custom-icon-badges.demolab.com/badge/Nsis%203.09-linen?logo=nsis-color)](https://nsis.sourceforge.io/Download)
[![Nuitka](https://custom-icon-badges.demolab.com/badge/Nuitka%202.1-linen?logo=nuitka)](https://nuitka.net/)
<sup><sub>or</sup></sub>
[![PyInstaller](https://custom-icon-badges.demolab.com/badge/PyInstaller%206.5.0-linen?logo=pyinstaller-windowed)](https://pyinstaller.org/en/stable/)

```console
python -m user_proxy_cmd.dev.build [--x86 | --x64 | --both] [--pyinstaller | --mingw] [--nobuild | --noinstaller | --readme] [--publish]
```
### Virus scan
It updates _Microsoft Defender_ engine and signatures before scanning:
```console
python -m user_proxy_cmd.dev.scan [--x86 | --x64 | --both]
```
### Publish a release
```console
python -m user_proxy_cmd.dev.publish [--x86 | --x64 | --both] [--version VERSION] [--info]
```
