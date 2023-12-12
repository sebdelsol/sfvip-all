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
[<img src="https://img.shields.io/badge/{name} {version} x64-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://custom-icon-badges.demolab.com/badge/{exe_x64_clean}.svg?logo=shield-check&logoColor=white&style=flat-square" height="30">](https://github.com/{github_path}/raw/master/{exe_x64_link})
<sub><sup>_by Microsoft Defender • {exe_x64_engine} • {exe_x64_signature}_</sup></sub>

[<img src="https://img.shields.io/badge/{name} {version} x86-informational?logo=docusign&logoColor=white&style=flat-square" height="30"><img src="https://custom-icon-badges.demolab.com/badge/{exe_x86_clean}.svg?logo=shield-check&logoColor=white&style=flat-square" height="30">](https://github.com/{github_path}/raw/master/{exe_x86_link})
<sub><sup>_by Microsoft Defender • {exe_x86_engine} • {exe_x86_signature}_</sup></sub>

# Build
[![Python](https://img.shields.io/badge/Python-{py_version}-fbdf79?logo=python&logoColor=fbdf79)](https://www.python.org/downloads/release/python-{py_version_compact}/)
[![Nsis](https://img.shields.io/badge/Nsis-{nsis_version}-informational?logo=NSIS&logoColor=white)](https://nsis.sourceforge.io/Download)
[![PyInstaller](https://custom-icon-badges.demolab.com/badge/PyInstaller-{pyinstaller_version}-informational.svg?logo=tools)](https://pyinstaller.org/en/stable/)
[![Nuitka](https://custom-icon-badges.demolab.com/badge/or%20Nuitka-{nuitka_version}-informational.svg?logo=tools)](https://nuitka.net/)
[![Style](https://custom-icon-badges.demolab.com/badge/Style-Black-000000.svg?logo=file-code)](https://black.readthedocs.io/en/stable/)
![Sloc](https://custom-icon-badges.demolab.com/badge/Sloc-{sloc}-000000.svg?logo=file-code)

```console
python -m user_proxy_cmd.dev.build [--x86 | --x64 | --both] [--pyinstaller | --mingw] [--nobuild | --noinstaller | --readme]
```