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
[<img src="https://img.shields.io/badge/SfvipUserProxy 0.4 x64-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://custom-icon-badges.demolab.com/badge/clean-brightgreen.svg?logo=shield-check&logoColor=white&style=flat-square" height="30">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.4/x64/Install%20SfvipUserProxy.exe)
<sub><sup>_by Microsoft Defender • 1.1.23100.2009 • 1.401.1671.0_</sup></sub>

[<img src="https://img.shields.io/badge/SfvipUserProxy 0.4 x86-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://custom-icon-badges.demolab.com/badge/clean-brightgreen.svg?logo=shield-check&logoColor=white&style=flat-square" height="30">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.4/x86/Install%20SfvipUserProxy.exe)
<sub><sup>_by Microsoft Defender • 1.1.23100.2009 • 1.401.1671.0_</sup></sub>

# Build
[![Python](https://img.shields.io/badge/Python-3.11.7-fbdf79?logo=python&logoColor=fbdf79)](https://www.python.org/downloads/release/python-3117/)
[![Nsis](https://img.shields.io/badge/Nsis-3.09-informational?logo=NSIS&logoColor=white)](https://nsis.sourceforge.io/Download)
[![PyInstaller](https://custom-icon-badges.demolab.com/badge/PyInstaller-6.3.0-informational.svg?logo=tools)](https://pyinstaller.org/en/stable/)
[![Nuitka](https://custom-icon-badges.demolab.com/badge/or%20Nuitka-1.9.4-informational.svg?logo=tools)](https://nuitka.net/)
[![Style](https://custom-icon-badges.demolab.com/badge/Style-Black-000000.svg?logo=file-code)](https://black.readthedocs.io/en/stable/)
![Sloc](https://custom-icon-badges.demolab.com/badge/Sloc-196-000000.svg?logo=file-code)

```console
python -m user_proxy_cmd.dev.build [--x86 | --x64 | --both] [--pyinstaller | --mingw] [--nobuild | --noinstaller | --readme]
```