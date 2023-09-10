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
[<img src="https://img.shields.io/badge/Version-0.3-informational"><img src="https://img.shields.io/badge/x64-informational?logo=windows&logoColor=white"><img src="https://img.shields.io/badge/Exe-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.3/x64/SfvipUserProxy.exe) <sup>or</sup> [<img src="https://img.shields.io/badge/Zip-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.3/x64/SfvipUserProxy.zip)

[<img src="https://img.shields.io/badge/Version-0.3-informational"><img src="https://img.shields.io/badge/x86-informational?logo=windows&logoColor=white"><img src="https://img.shields.io/badge/Exe-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.3/x86/SfvipUserProxy.exe) <sup>or</sup> [<img src="https://img.shields.io/badge/Zip-informational">](https://github.com/sebdelsol/sfvip-all/raw/master/user_proxy_cmd/build/0.3/x86/SfvipUserProxy.zip)


# Build
[![Python](https://img.shields.io/badge/Python-3.11.5-fbdf79)](https://www.python.org/downloads/release/python-3115/)
[![Nuitka](https://img.shields.io/badge/Nuitka-1.8.1-lightgrey)](https://nuitka.net/)
[![Style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)
![Sloc](https://img.shields.io/badge/Sloc-94-informational)

```console
python -m user_proxy_cmd.build [--x86 | --x64 | --both] [--nobuild | --noexe | --nozip] [--mingw]
```