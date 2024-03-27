## 1.4.12.44
* Fix UI minor bug when launching several _Sfvip All_.
* Fix uninstall old version if the installation folder differs.

## 1.4.12.43
* Option to modify _Sfvip All_ install directory.
* When updating the Install directory won't be asked again
and _Sfvip All_ will be automatically relaunched. 

## 1.4.12.42
* Fix Minor bugs.
* Better translations.
* Better MAC accounts all categories progress.
* Fix suggestion to restart when adding or modifying a User.

## 1.4.12.41
* Faster MAC accounts cache for all categories.
* MAC accounts cache handles partial update.
* All categories are added only when needed.
* Tooltips added.

## 1.4.12.40
* Option to prefer the IPTV provider EPG over external EPG.
* Faster EPG processing and loading that use less memory.
* Fix EPG processing restarting when closing the UI.
* Better fuzzy match for external EPG.

## 1.4.12.39
* Bump _mitmproxy_ to 10.2.4.
* _Sfvip All_ windows smoothly follow _Sfvip Player_.

## 1.4.12.38
* Bump _mitmproxy_ to 10.2.3: upgrade proxy security.
* Better translations.

## 1.4.12.37
* Save _Sfvip Player_ Changelog.

## 1.4.12.36
* Add Sfvip Player Changelog tooltip.

## 1.4.12.35
* Add Sfvip All Changelog tooltip.
* Bump _Nuitka_ to 2.1.

## 1.4.12.34
* Fix libmpv update UI.
* Bump _Nuitka_ to 2.0.6.

## 1.4.12.33
* Info window stays longer.
* Bump _Nuitka_ to 2.0.5.
* Fix & Clean EPG cache.
* Fix tooltip.

## 1.4.12.32
* EPG is cached for faster access.

## 1.4.12.31
* Platform added in the logs.
* Bump _Nuitka_ to 2.0.4.

## 1.4.12.30
* Use Github releases for downloads and updates.

## 1.4.12.29
* Fix all categories name for MAC accounts.

## 1.4.12.28
* Fix too verbose _mitmproxy_ process logs.

## 1.4.12.27
* Fix [EPG for m3U accounts](https://github.com/sebdelsol/sfvip-all/issues/12).

## 1.4.12.26
* Bump _Nuitka_ to 2.0.

## 1.4.12.25
* Fix _Sfvip All_ window UI.

## 1.4.12.24
* Bump _mitmproxy_ to 10.2.2.
* Build with _Pyinstaller_.

## 1.4.12.23
* Clean old caches & libmpv dlls.

## 1.4.12.22
* Faster startup.

## 1.4.12.21
* Show/hide proxies in the _Sfvip All_ window.
* Fix EPG rounded box.

## 1.4.12.20
* Fix bug where it was not possible to update the external epg if it had failed.
* EPG for M3U: fix bug where it didn't close when stopping the streaming.
* EPG for M3U: button to close the schedule.
* Tooltips added to explain EPG confidence.

## 1.4.12.12
* EPG for M3U: show the upcoming schedule with `e` keyboard shortcut.

## 1.4.12.11
* External EPG for M3U _online_ accounts: show current channel programme only.

## 1.4.12.10
* External EPG for MAC accounts.

## 1.4.12.9
* Entry added for EPG confidence.
* Fix another external EPG download issue.

## 1.4.12.8
* Cleaner UI.

## 1.4.12.7
* Better match with external EPG channels.
* External EPG confidence slider (for fuzzy matches cutoff).
* Show confidence level when an EPG channel is found.

## 1.4.12.6
* Fix external EPG that failed to download (because of missing headers content length).

## 1.4.12.5
* MAC accounts' all categories are cached.
* MAC accounts' all categories caches can be updated.
* Show MAC accounts all categories progress when their cache is build.
* Fix bug when trying to update _Libmpv_ with the player opened.

## 1.4.12.4
* Fix [issue](https://github.com/sebdelsol/sfvip-all/issues/2) when external EPG is too big.
* External EPG UI is more responsive.
* Show External EPG progress.

## 1.4.12.3
* External EPG url works when there's no user.

## 1.4.12.2
* Validate External EPG url.

## 1.4.12.1 
* Fix hook bug in x86 version.
* External EPG matches more channels.

## 1.4.12
* External EPG option.

## 1.4.11
* Fix episodes list that _Sfvip Player_ doesn't correctly handle.
* Fix missing _Sfvip Player_ UI.

## 1.4.10
* Fix _Sfvip Player_ upgrading (bitness and error handling).
* Fix UI localization when downloading.
* Bump _Nuitka_ to 1.9.5.

## 1.4.9
* _Sfvip Player_ check update option.
* Fix possible cropped splashscreen.
* Bump _mitmproxy_ to 10.1.6.
* Bump _Nuitka_ to 1.9.4.

## 1.4.8
* Work with _Sfvip Player_ >= 1.2.5.7.
* Check _Sfvip Player_ version. 
* Bump _Python_ to 3.11.7.

## 1.4.7
* Bump _Nuitka_ to 1.9.2 for faster startup time.
* Fix potential log files collisions & garbled filenames.

## 1.4.6
* Fix localization when a running _Sfvip All_ prevents the (un)installation.

## 1.4.5
* Installer uses _Sfvip Player_ language when updating.
* (fix 1.4.3 & 1.4.4).

## 1.4.2
* Bump _Nuitka_ to 1.8.6.
* Reduce installer size.

## 1.4.1
* Better check for installing or uninstalling.
* Less AV false positives.

## 1.4.0
* Check _Sfvip All_ is not running when installing or uninstalling.
* Overwrite already installed file when needed.
* Builder overhaul.

## 1.3.12
* Logs are easier found.

## 1.3.11
* All categories translations in vod & series panels.

## 1.3.10
* Change the distribution & update strategy to mitigate the AV issue.
* Bump _Nuitka_ to 1.8.4.

## 1.3.09
* Enhance UI presentation.

## 1.3.08
* Enhance translator for better translations.

## 1.3.07
* Fix translation bug for non latin alphabet.

## 1.3.06
* _Sfvip All_ is translated in every _Sfvip Player_ languages.
* Fix bug when _Sfvip Player_ had never been launched once.
* Bump _Python_ to 3.11.6.

## 1.3.05
* Handle correctly already downloaded _Sfvip All_ update.
* Minor bug fixes.

## 1.3.04
* Ask to restart after _Libmpv_ or _Sfvip All_ update.
* Simpler user experience for finding or downloading _Sfvip Player_.

## 1.3.03
* Bump _Nuitka_ to 1.8.3.
* keep cleaning ConfigLoader.

## 1.3.02
* Add PE fixes to mitigate AV false positives.
* Enhanced ConfigLoader.
* Minor bug fixes.

## 1.3.01
* Bump _mitmproxy\_rs_ to 0.3.11

## 1.3.0
* _Sfvip All_ check update option.
* User's exit stops any installation.
* Bump _mitmproxy_ to 10.1.0 (rustup is no longer needed).

## 1.2.9
* _Libmpv_ check update option.
* Download window mimics _Sfvip Player_ UI.

## 1.2.8
* Detection of x86-64-v3 architecture for _Libmpv_ download.
* Fix wrong bitness in the Proxies window.

## 1.2.7
* Bump _mitmproxy_ to 10.0.0.
* The upgrader always respects dependencies.
* Logs for _Sfvip Player_ download. 

## 1.2.6
* Download latest _Sfvip Player_ if not already installed.

## 1.2.5
* Bump _Python_ to 3.11.5.
* Bump _Nuitka_ to 1.8.
* Requirements tailored for x64 and x86 versions.

## 1.2.4
* Upgrade requirements.
* Still working with _Sfvip Player_ 1.2.7.61.

## 1.2.3
* Fix possible monitor areas overflow on x64.

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
