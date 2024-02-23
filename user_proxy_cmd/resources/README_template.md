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
[<img src="https://custom-icon-badges.demolab.com/badge/{name} v{version} x64-informational.svg?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="29"><img src="https://custom-icon-badges.demolab.com/badge/{exe_x64_clean}.svg?logo=shield-check&logoColor=white&style=flat-square" height="29">]({exe_x64_release})
<sup><sup>_by MS Defender • {exe_x64_engine} • {exe_x64_signature}_</sup></sup>

[<img src="https://custom-icon-badges.demolab.com/badge/{name} v{version} x86-informational.svg?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="29"><img src="https://custom-icon-badges.demolab.com/badge/{exe_x86_clean}.svg?logo=shield-check&logoColor=white&style=flat-square" height="29">]({exe_x86_release})
<sup><sup>_by MS Defender • {exe_x86_engine} • {exe_x86_signature}_</sup></sup>

# Build
[![Python](https://img.shields.io/badge/Python-{py_version}-fbdf79?logo=python&logoColor=fbdf79)](https://www.python.org/downloads/release/python-{py_version_compact}/)
[![Style](https://custom-icon-badges.demolab.com/badge/Style-Black-000000.svg?logo=file-code&logoColor=a0a0a0)](https://black.readthedocs.io/en/stable/)
![Sloc](https://custom-icon-badges.demolab.com/badge/Sloc-{sloc}-000000.svg?logo=file-code&logoColor=a0a0a0)

[![Nuitka](https://custom-icon-badges.demolab.com/badge/Nuitka-{nuitka_version}-informational.svg?logo=tools&logoColor=61dafb)](https://nuitka.net/)
<sup><sub>**or**</sub></sup>
[![PyInstaller](https://custom-icon-badges.demolab.com/badge/PyInstaller-{pyinstaller_version}-informational.svg?logo=tools&logoColor=61dafb)](https://pyinstaller.org/en/stable/)

[![Nsis](https://img.shields.io/badge/Nsis-{nsis_version}-informational?logo=NSIS&logoColor=fbdf79)](https://nsis.sourceforge.io/Download)

```console
python -m user_proxy_cmd.dev.build [--x86 | --x64 | --both] [--pyinstaller | --mingw] [--nobuild | --noinstaller | --readme]
```