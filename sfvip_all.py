# nuitka ?
if "__compiled__" in globals():
    import os

    # onefile ?
    if "NUITKA_ONEFILE_PARENT" in os.environ:
        import sys
        from pathlib import Path

        from build_config import Build

        # hack to make multiprocessing work with nuitka when the exe has been renamed
        # by forcing the built exe name on sys.argv[0]
        exe = Path(sys.argv[0]).parent / f"{Build.name}.exe"
        sys.argv[0] = str(exe.resolve())

if __name__ == "__main__":
    from build_config import Build
    from sfvip import run
    from sfvip.ui import UI

    ui = UI(Build.name, Build.splash)
    ui.in_thread(run, ui, Build.name)
