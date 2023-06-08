# use a separate named package to reduce what's imported by multiproccessing
import asyncio
import logging
import multiprocessing
import threading
from typing import NamedTuple, Protocol

from mitmproxy import http, options
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

logger = logging.getLogger(__name__)
# do not pollute the log
logging.getLogger("mitmproxy.proxy.server").setLevel(logging.WARNING)


# use only the needed addons,
# Note: use addons.default_addons() instead if any issues
def _minimum_addons():
    return [
        core.Core(),
        disable_h2c.DisableH2C(),
        proxyserver.Proxyserver(),
        dns_resolver.DnsResolver(),
        next_layer.NextLayer(),
        tlsconfig.TlsConfig(),
    ]


class _AddOn(Protocol):
    def request(self, flow: http.HTTPFlow) -> None:
        pass

    def response(self, flow: http.HTTPFlow) -> None:
        pass

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        pass


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

    def __init__(self, addon: _AddOn, modes: set[Mode]) -> None:
        self._stop = multiprocessing.Event()
        self._addon = addon
        self._modes = modes
        super().__init__()

    def run(self) -> None:
        # launch one proxy per mode
        modes = [mode.to_mitm() for mode in self._modes]
        logger.info("mimtproxy start with mode(s): %s", " - ".join(modes))
        # do not verify upstream server SSL/TLS certificates
        opts = options.Options(ssl_insecure=True, mode=modes)
        loop = asyncio.get_event_loop()
        master = Master(opts, event_loop=loop)
        master.addons.add(self._addon, *_minimum_addons())

        def _wait_for_stop() -> None:
            self._stop.wait()
            master.shutdown()

        threading.Thread(target=_wait_for_stop).start()
        loop.run_until_complete(master.run())

    def stop(self) -> None:
        self._stop.set()
        self.join()
        logger.info("mimtproxy stopped")
