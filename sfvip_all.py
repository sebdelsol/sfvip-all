if __name__ == "__main__":
    from multiprocessing import freeze_support

    from sfvip import run

    freeze_support()  # pyinstaller
    run()
