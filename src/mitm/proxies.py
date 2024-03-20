# use a separate named package to reduce what's imported by multiproccessing
import asyncio
import logging
import multiprocessing
import socket
import threading
from typing import Any, NamedTuple, Optional, Sequence

from mitmproxy import options
from mitmproxy.addons import core, next_layer, proxyserver, tlsconfig
from mitmproxy.master import Master
from mitmproxy.net import server_spec

from shared import LogProcess

from ..winapi.process import set_current_process_high_priority
from .addon import SfVipAddOn

logger = logging.getLogger(__name__)


# use only the needed addons,
def _minimum_addons(user_addon: SfVipAddOn) -> Sequence[Any]:
    return (
        core.Core(),
        proxyserver.Proxyserver(),
        user_addon,
        next_layer.NextLayer(),
        tlsconfig.TlsConfig(),
    )
    # if any issues:
    # from mitmproxy.addons import default_addons, script
    # return [user_addon if isinstance(addon, script.ScriptLoader) else addon for addon in default_addons()]


class Mode(NamedTuple):
    port: int
    upstream: str

    def to_mitm(self) -> str:
        proxy = f"upstream:{self.upstream}" if self.upstream else "regular"
        return f"{proxy}@{self.port}"


def validate_upstream(url: str) -> bool:
    try:
        server_spec.parse(url, default_scheme="http")
        return True
    except ValueError:
        return False


class MitmLocalProxy(multiprocessing.Process):
    """run mitmdump in a process"""

    def __init__(self, addon: SfVipAddOn, modes: set[Mode]) -> None:
        self._stop = multiprocessing.Event()
        self._master: Optional[Master] = None
        self._master_lock = multiprocessing.Lock()
        self._addon = addon
        self._modes = modes
        super().__init__()

    def run(self) -> None:
        socket.setdefaulttimeout(0)  # TODO is it better ??
        with LogProcess(logger, "Mitmproxy"):
            if set_current_process_high_priority():
                logger.info("Set process to high priority")
            threading.Thread(target=self._wait_for_stop).start()
            if self._modes:
                # launch one proxy per mode
                modes = [mode.to_mitm() for mode in self._modes]
                loop = asyncio.get_event_loop()
                with self._master_lock:
                    self._master = Master(options.Options(), event_loop=loop)
                    self._master.addons.add(*_minimum_addons(self._addon))
                    # do not verify upstream server SSL/TLS certificates
                    self._master.options.update(ssl_insecure=True, mode=modes)
                loop.run_until_complete(self._master.run())
            else:
                self._addon.running()
                self._stop.wait()

    def _wait_for_stop(self) -> None:
        self._stop.wait()
        with self._master_lock:
            if self._master:
                self._master.shutdown()
            else:
                self._addon.done()

    def wait_running(self, timeout: int) -> bool:
        return self._addon.wait_running(timeout)

    def stop(self) -> None:
        if not self._stop.is_set():
            self._stop.set()
            self.join()
