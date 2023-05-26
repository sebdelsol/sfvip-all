## 1.1.6
* Fix ***Zip*** that wasn't launching (because of the log files added in 1.1.5)
* ***All*** category is added in ***live*** too for older version of _sfvip player_.

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
    - ***mitmproxy*** instead of proxy.py,
    - Subprocesses for proxies,
    - ***Clang*** to build.
* Forward to the original accounts proxies.
* _Error log_ in cachedir.

## 1.1.2
* Faster by using ***noitka*** for the distribution (executable & archive).

## 1.1.1
* Change repo structure.
* Smaller distribution.

## 1.1
* Clean _svip player_ database as soon as possible.

## 1.0
* Find and wraps _sfvip player_ with a proxy to add an All category in Vod and Series.
