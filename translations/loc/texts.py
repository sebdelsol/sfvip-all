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
    SearchOrDownload: str = "Do you want to search or download it ?"
    NoSocketPort: str = "No socket port available !"
    CantStartProxies: str = "Can't start local proxies !"
    NotFound: str = "%s not found"
    AllSeries: str = "All Series"
    AllMovies: str = "All Movies"
    AllChannels: str = "All Channels"
    AlreadyRunning: str = "%s is running. Please close it to continue."
    PlayerTooOld: str = "%s is too old. Version %s or above is needed."
    UpgradeFailed: str = "%s upgrade failed. Do you want to retry ?"
    Loading: str = "Loading"
    Processing: str = "Processing"
    Ready: str = "Ready"
    Failed: str = "Failed"
    NoEpg: str = "No EPG"
    EpgUrl: str = "External EPG"
    InvalidUrl: str = "Invalid url"
    UpdatedToday: str = "Updated today"
    Updated1DayAgo: str = "Updated 1 day ago"
    UpdatedDaysAgo: str = "Updated %s days ago"
    UpdateAllSeries: str = "Update All series"
    UpdateAllMovies: str = "Update All movies"

    @staticmethod
    def as_dict() -> dict[str, str]:
        return Texts._field_defaults  # pylint: disable=no-member
