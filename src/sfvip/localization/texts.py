from typing import NamedTuple


class Texts(NamedTuple):
    language = "english"

    User: str = "User"
    UserProxy: str = "User Proxy"
    NoProxy: str = "Proxy missing"
    Proxy: str = "%s Proxy"
    RestartFixProxy: str = "Restart to fix the proxies"
    ShouldUseVersion: str = "You should use the %s version"
    SearchWholeCatalog: str = "Search your whole catalog"
    Download: str = "Download"
    Install: str = "Install"
    Extract: str = "Extract"
    Update: str = "Update"
    Restart: str = "Restart"
    Cancel: str = "Cancel"
    Find: str = "Find"
    CheckUpdate: str = "Check update"
    UnknownVersion: str = "Unknown version"
    PleaseWait: str = "Please wait"
    CheckLastestLibmpv: str = "Check latest libmpv"
    RestartInstall: str = "Restart to install %s ?"
    FindOrDownload: str = "Find or download it"
    NoSocketPort: str = "No socket port available !"
    CantStartProxies: str = "Can't start local proxies !"
    PlayerConfigNotFound: str = "Sfvip Player configuration directory not found"
    PlayerNotFound: str = "Sfvip Player not found"

    @staticmethod
    def as_dict() -> dict[str, str]:
        return Texts._field_defaults  # pylint: disable=no-member
