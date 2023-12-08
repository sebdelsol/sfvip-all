# {name}
_Command to add an user proxy for **all users** in [**Sfvip Player**](https://github.com/K4L4Uz/SFVIP-Player/tree/master) **database**:_
```console
{name} http://127.0.0.1:8888
```
_Remove it:_
```console
{name} --remove
```

# Download
[<img src="https://img.shields.io/badge/{name} {version} x64-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://img.shields.io/badge/{exe_x86_clean}?style=flat-square" height="30">](https://github.com/{github_path}/raw/master/{exe_x64_link})<img src="https://custom-icon-badges.demolab.com/badge/Scanned by Microsoft Defender • {exe_x64_engine} • {exe_x64_signature}-white.svg?logo=shield-check&logoColor=black&style=flat-square" height="15">

[<img src="https://img.shields.io/badge/{name} {version} x86-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://img.shields.io/badge/{exe_x86_clean}?style=flat-square" height="30">](https://github.com/{github_path}/raw/master/{exe_x86_link})<img src="https://custom-icon-badges.demolab.com/badge/Scanned by Microsoft Defender • {exe_x86_engine} • {exe_x86_signature}-white.svg?logo=shield-check&logoColor=black&style=flat-square" height="15">

# Build
[![Python](https://img.shields.io/badge/Python-{py_version}-fbdf79?logo=python&logoColor=fbdf79)](https://www.python.org/downloads/release/python-{py_version_compact}/)
[![Nsis](https://img.shields.io/badge/Nsis-{nsis_version}-informational)](https://nsis.sourceforge.io/Download)
[![Nuitka](https://img.shields.io/badge/Nuitka-{nuitka_version}-informational)](https://nuitka.net/)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-{pyinstaller_version}-informational)](https://pyinstaller.org/en/stable/)
[![Style](https://img.shields.io/badge/Style-Black-000000)](https://black.readthedocs.io/en/stable/)
![Sloc](https://img.shields.io/badge/Sloc-{sloc}-000000)

```console
python -m user_proxy_cmd.dev.build [--x86 | --x64 | --both] [--pyinstaller | --mingw] [--nobuild | --noinstaller | --readme]
```