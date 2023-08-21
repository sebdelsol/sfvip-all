# SfvipUserProxy
***SfvipUserProxy*** add or remove a global user proxy for all users in ***[Sfvip Player](https://serbianforum-org.translate.goog/threads/sf-vip-plejer.878393/?_x_tr_sl=sr&_x_tr_tl=en)*** database.

<img src="https://img.shields.io/badge/Version-0.2-informational" valign="middle"><img src="https://img.shields.io/badge/x64-informational?logo=windows&logoColor=white" valign="middle"> &nbsp;[***Executable***](https://github.com/sebdelsol/sfvip-all/raw/master/sfvip_user_proxy/build/0.2/x64/SfvipUserProxy.exe).

<img src="https://img.shields.io/badge/Version-0.2-informational" valign="middle"><img src="https://img.shields.io/badge/x86-informational?logo=windows&logoColor=white" valign="middle"> &nbsp;[***Executable***](https://github.com/sebdelsol/sfvip-all/raw/master/sfvip_user_proxy/build/0.2/x86/SfvipUserProxy.exe).

#### Add a global user proxy:
```console
SfvipUserProxy http://127.0.0.1:8888
```
#### Remove it:
```console
SfvipUserProxy --remove
```

# Build
[![Python](https://img.shields.io/badge/Python-3.11.4-fbdf79)](https://www.python.org/downloads/release/python-3114/)
[![dist](https://img.shields.io/badge/Dist-Nuitka-lightgrey)](https://nuitka.net/)
[![style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)

```console
python -m sfvip_user_proxy.build [--x86 | --x64 | --both] [--upgrade] [--mingw]
```