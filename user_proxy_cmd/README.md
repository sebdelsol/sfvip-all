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
[<img src="https://img.shields.io/badge/SfvipUserProxy 0.4 x64-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://img.shields.io/badge/Clean-brightgreen?style=flat-square" height="30">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.4/x64/Install%20SfvipUserProxy.exe)<img src="https://custom-icon-badges.demolab.com/badge/Scanned by Microsoft Defender • 1.1.23100.2009 • 1.401.1336.0-white.svg?logo=shield-check&logoColor=black&style=flat-square" height="15">

[<img src="https://img.shields.io/badge/SfvipUserProxy 0.4 x86-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://img.shields.io/badge/Clean-brightgreen?style=flat-square" height="30">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.4/x86/Install%20SfvipUserProxy.exe)<img src="https://custom-icon-badges.demolab.com/badge/Scanned by Microsoft Defender • 1.1.23100.2009 • 1.401.1336.0-white.svg?logo=shield-check&logoColor=black&style=flat-square" height="15">

# Build
[![Python](https://img.shields.io/badge/Python-3.11.6-fbdf79?logo=python&logoColor=fbdf79)](https://www.python.org/downloads/release/python-3116/)
[![Nuitka](https://img.shields.io/badge/Nuitka-1.9.2-informational)](https://nuitka.net/)
[![Nsis](https://img.shields.io/badge/Nsis-3.09-informational)](https://nsis.sourceforge.io/Download)
[![Style](https://img.shields.io/badge/Style-Black-000000)](https://black.readthedocs.io/en/stable/)
![Sloc](https://img.shields.io/badge/Sloc-196-informational)

You need [***NSIS***](https://nsis.sourceforge.io/Download) to create the installer.

```console
python -m user_proxy_cmd.dev.build [--x86 | --x64 | --both] [--nobuild | --noinstaller | --readme] [--mingw]
```