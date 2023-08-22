# {name}
***{name}*** command add or remove an user proxy for **all users** in ***[Sfvip Player](https://serbianforum-org.translate.goog/threads/sf-vip-plejer.878393/?_x_tr_sl=sr&_x_tr_tl=en)*** database.

<img src="https://img.shields.io/badge/Version-{version}-informational" valign="middle"><img src="https://img.shields.io/badge/x64-informational?logo=windows&logoColor=white" valign="middle"> &nbsp;[***Executable***](https://github.com/{github_path}/raw/master/{exe64_link}).

<img src="https://img.shields.io/badge/Version-{version}-informational" valign="middle"><img src="https://img.shields.io/badge/x86-informational?logo=windows&logoColor=white" valign="middle"> &nbsp;[***Executable***](https://github.com/{github_path}/raw/master/{exe32_link}).

#### Add a global user proxy:
```console
{name} http://127.0.0.1:8888
```
#### Remove it:
```console
{name} --remove
```

# Build
[![Python](https://img.shields.io/badge/Python-{py_version}-fbdf79)](https://www.python.org/downloads/release/python-{py_version_compact}/)
[![Nuitka](https://img.shields.io/badge/Nuitka-{nuitka_version}-lightgrey)](https://nuitka.net/)
[![Style](https://img.shields.io/badge/Style-Black-000000)](https://github.com/psf/black)

```console
python -m user_proxy_cmd.build [--x86 | --x64 | --both] [--upgrade] [--mingw]
```