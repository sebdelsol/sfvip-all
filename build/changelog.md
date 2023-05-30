## 1.1.6
* Fix ***Zip*** launcher broken with 1.1.5.
* ***Config All.json*** is safe to tamper with.
* ***Logs*** are to be found in the ***Exe*** directory.
* Player position is preserved when an auto relaunch occurs.
* Handle change of _Config Location_ in Sfvip Player Settings.
* ***All*** category added in ***live*** panel for older version of _sfvip player_.

## 1.1.5
* Proper logging.
* Validate accounts proxies.
* Restore accounts proxies when changed by sfvip player 
  and auto relaunch if needed.

## 1.1.4
* The ***Exe*** can be renamed (fix nuitka multiprocessing).
* Accounts proxies correctly restored when launching a lot of Sfvip All in a row.
* Splash screen (useful when there're a lot of proxies to launch).

## 1.1.3
* Reduce proxies overhead by using:
    - ***Mitmproxy*** instead of proxy.py,
    - Subprocesses for proxies,
    - ***Clang*** to build.
* Forward to the original accounts proxies.
* _Error log_ available.

## 1.1.2
* Faster with ***Nuitka*** build for the distribution.

## 1.1.1
* Change repository structure.
* Smaller distribution.

## 1.1
* Clean _Svip Player_ database as soon as possible.

## 1.0
* Find and wraps _Sfvip Player_ with a proxy to add an All category in Vod and Series.
