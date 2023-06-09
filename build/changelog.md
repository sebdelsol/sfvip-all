## 1.2.3
* Fix possible monitor areas overflow on x64

## 1.2.2
* Hook cpu load reduced even in the worst case.
* Cleanly fail when no ports are available.
* Minor bug fixes.

## 1.2.1
* Reduce drasticaly _Sfvip All_ cpu load thanks to a way more efficient hook.
* Handle _Database.json_ trailing commas like _Sfvip Player_ does.
* Minor bug fixes.

## 1.2.0
* Proxies are correctly restored when several _Sfvip All_ are running concurrently.
* No longer restart when _Sfvip Player_ Logging setting is switched off.
* Fix _Sfvip Player_ duplicate users name.
* Minor bug fixes.

## 1.1.9
* Builds for _x64_ and _x86_.
* Minor bug fixes.

## 1.1.8
* No auto relaunch when the proxies have been changed. A relaunch button is showed instead.
* Proxies window is scrollable when the list is too long.
* Proxies window mimics _Sfvip Player_ UI.
* Fix a potential deadlock.

## 1.1.7
* _Sfvip All_ lives in the top left corner of _Sfvip Player_: 
    * Mouse over to show the proxies window.
    * Pulse color shows the proxies status.
* A lot of bug fixes.

## 1.1.6
* Enforce _Sfvip Player_ logging setting to stay on for proper change detection.
* _All_ category added in _live_ for older version of _Sfvip Player_.
* Handle change of _Config Location_ in _Sfvip Player_ settings.
* Player position is preserved when a relaunch occurs.
* _Logs_ are to be found in the _Exe_ directory.
* _Config All.json_ is safe to tamper with.
* Fix _Zip_ launcher broken by 1.1.5.

## 1.1.5
* Restore accounts proxies when changed by the user and relaunch if needed.
* Validate accounts proxies which is not done by _Sfvip Player_.
* Proper logging.

## 1.1.4
* Accounts proxies properly restored when launching a lot of _Sfvip Player_ in a row.
* Splash screen because the player is sometimes way too long to launch.
* The _Exe_ can be renamed.

## 1.1.3
* Barely any proxy overhead by using _mitmproxy_, _clang_, and subprocesses.
* Forward to the accounts proxies.
* _Error logs_ available.

## 1.1.2
* Way faster thanks to _Nuitka_ build.

## 1.1.1
* Smaller distribution.

## 1.1
* _Svip Player_ proxies are restored ASAP.

## 1.0
* Find and wraps _Sfvip Player_ with a local proxy to add an _All_ category in _vod_ and _series_.
