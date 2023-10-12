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
[<img src="https://img.shields.io/badge/Version-0.4-informational"><img src="https://img.shields.io/badge/x64-informational?logo=windows&logoColor=white"><img src="https://img.shields.io/badge/installer-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.4/x64/Install%20SfvipUserProxy.exe)

[<img src="https://img.shields.io/badge/Version-0.4-informational"><img src="https://img.shields.io/badge/x86-informational?logo=windows&logoColor=white"><img src="https://img.shields.io/badge/installer-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.4/x86/Install%20SfvipUserProxy.exe)


# Build
[![Python](https://img.shields.io/badge/Python-3.11.6-fbdf79)](https://www.python.org/downloads/release/python-3116/)
[![Nuitka](https://img.shields.io/badge/Nuitka-1.8.4-lightgrey)](https://nuitka.net/)
[![Style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)
![Sloc](https://img.shields.io/badge/Sloc-208-informational)

You'll need [***NSIS***](https://nsis.sourceforge.io/Download) to create the installer.

```console
python -m user_proxy_cmd.dev.build [--x86 | --x64 | --both] [--nobuild | --noinstaller | --readme] [--mingw]
```