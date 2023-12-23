# use a separate named package to reduce what's imported by multiproccessing
import asyncio
import logging
import multiprocessing
import threading
from typing import Any, NamedTuple, Optional, Sequence

from mitmproxy import options
from mitmproxy.addons import (
    core,
    disable_h2c,
    dns_resolver,
    next_layer,
    proxyserver,
    tlsconfig,
)
from mitmproxy.master import Master
from mitmproxy.net import server_spec

from .addon import SfVipAddOn

logger = logging.getLogger(__name__)
# do not pollute the log
logging.getLogger("mitmproxy.proxy.server").setLevel(logging.WARNING)


# use only the needed addons,
# Note: use addons.default_addons() instead if any issues
def _minimum_addons() -> Sequence[Any]:
    return (
        core.Core(),
        disable_h2c.DisableH2C(),
        proxyserver.Proxyserver(),
        dns_resolver.DnsResolver(),
        next_layer.NextLayer(),
        tlsconfig.TlsConfig(),
    )


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
        logger.info("Mitmproxy process started")
        threading.Thread(target=self._wait_for_stop).start()
        if self._modes:
            # launch one proxy per mode
            modes = [mode.to_mitm() for mode in self._modes]
            # do not verify upstream server SSL/TLS certificates
            opts = options.Options(ssl_insecure=True, mode=modes)
            loop = asyncio.get_event_loop()
            with self._master_lock:
                self._master = Master(opts, event_loop=loop)
                self._master.addons.add(self._addon, *_minimum_addons())
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
        logger.info("Mitmproxy process exit")

    def wait_running(self, timeout: int) -> bool:
        return self._addon.wait_running(timeout)

    def stop(self) -> None:
        if not self._stop.is_set():
            self._stop.set()
            self.join()
