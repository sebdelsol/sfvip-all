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
    Search: str = "Search"
    Retry: str = "Retry"
    CheckUpdate: str = "Check updates"
    UnknownVersion: str = "Unknown version"
    PleaseWait: str = "Please wait"
    CheckLastestLibmpv: str = "Check latest libmpv update"
    RestartInstall: str = "Do you want to restart to install %s ?"
    SearchOrDownload: str = "Do you want to Search or download it ?"
    NoSocketPort: str = "No socket port available !"
    CantStartProxies: str = "Can't start local proxies !"
    NotFound: str = "%s not found"
    AllSeries: str = "All Series"
    AllMovies: str = "All Movies"
    AllChannels: str = "All Channels"
    AlreadyRunning: str = "%s is running. Please close it to continue."
    PlayerTooOld: str = "%s is too old. Version ≥ %s is needed."

    @staticmethod
    def as_dict() -> dict[str, str]:
        return Texts._field_defaults  # pylint: disable=no-member
