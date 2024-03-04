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
[<img src="https://custom-icon-badges.demolab.com/badge/{name} v{version_x64}-informational?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="{h_download}"><img src="https://img.shields.io/badge/x64-informational?logo=Windows10&logoColor=lightblue&style=flat-square" height="{h_download}"><img src="https://custom-icon-badges.demolab.com/badge/{exe_x64_clean}?logo=shield-check&logoColor=white&style=flat-square" height="{h_download}">]({exe_x64_release})
<sup><sup>_by MS Defender • {exe_x64_engine} • {exe_x64_signature}_</sup></sup>

[<img src="https://custom-icon-badges.demolab.com/badge/{name} v{version_x86}-informational?logo=download-cloud&logoSource=feather&logoColor=white&style=flat-square" height="{h_download}"><img src="https://img.shields.io/badge/x86-informational?logo=Windows10&logoColor=lightblue&style=flat-square" height="{h_download}"><img src="https://custom-icon-badges.demolab.com/badge/{exe_x86_clean}?logo=shield-check&logoColor=white&style=flat-square" height="{h_download}">]({exe_x86_release})
<sup><sup>_by MS Defender • {exe_x86_engine} • {exe_x86_signature}_</sup></sup>

# Build
[![Python](https://custom-icon-badges.demolab.com/badge/Python%20{py_version}-white?logo=python-color)](https://www.python.org/downloads/release/python-{py_version_compact}/)
[![Ruff](https://custom-icon-badges.demolab.com/badge/Ruff-informational?logo=ruff-color)](https://github.com/astral-sh/ruff)
[![Nsis](https://custom-icon-badges.demolab.com/badge/Nsis%20{nsis_version}-informational?logo=nsis-color)](https://nsis.sourceforge.io/Download)
[![Nuitka](https://custom-icon-badges.demolab.com/badge/Nuitka%20{nuitka_version}-informational?logo=nuitka)](https://nuitka.net/)
[![PyInstaller](https://custom-icon-badges.demolab.com/badge/PyInstaller%20{pyinstaller_version}-informational?logo=pyinstaller-windowed)](https://pyinstaller.org/en/stable/)
[![Sloc](https://custom-icon-badges.demolab.com/badge/Sloc%20{sloc}-black?logo=file-code&logoColor=a0a0a0)](https://api.codetabs.com/v1/loc/?github={github_path})

```console
python -m user_proxy_cmd.dev.build [--x86 | --x64 | --both] [--pyinstaller | --mingw] [--nobuild | --noinstaller | --readme] [--publish]
```
### Publish a release
```console
python -m user_proxy_cmd.dev.publish [--x86 | --x64 | --both] [--version VERSION] [--info]
```
### Virus scan
It updates _Microsoft Defender_ engine and signatures before scanning:
```console
python -m user_proxy_cmd.dev.scan [--x86 | --x64 | --both]
```
