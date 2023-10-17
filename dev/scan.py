from build_config import Build, Environments

from .tools.scanner import VirusScan

if __name__ == "__main__":
    VirusScan.scan_all(Build, Environments)
