import os
import ssl
import signal
import asyncio
import ctypes
import ctypes.util
import multiprocessing
from hypercorn.run import run
from hypercorn.config import Config

from ..constants import Ports, TLS

def set_ssl_groups(context: ssl.SSLContext, groups: str) -> None:
    libssl_name = ctypes.util.find_library("ssl")
    if not libssl_name:
        raise ssl.SSLError("libssl Not Found")
    libssl = ctypes.CDLL(libssl_name)
    fn = libssl.SSL_CTX_ctrl
    fn.restype = ctypes.c_long
    fn.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long, ctypes.c_char_p]
    ptr_size = ctypes.sizeof(ctypes.c_void_p)
    raw_ctx = ctypes.c_void_p.from_address(id(context) + 2 * ptr_size).value
    if fn(raw_ctx, 92, 0, groups.encode()) != 1:
        raise ssl.SSLError(f"SSL_CTX_ctrl(SET_GROUPS_LIST) Failed: {groups!r}")

class HypercornConfig(Config):
    needs_quic_patch: bool = False

    def create_ssl_context(self) -> ssl.SSLContext | None:
        context = super().create_ssl_context()
        if context is not None:
            context.options |= ssl.OP_NO_TICKET
            set_ssl_groups(context, TLS.groups)
        return context

    def patch_quic_ssl_groups(self) -> None:
        from hypercorn.protocol import quic as hypercorn_quic
        original_init = hypercorn_quic.QuicProtocol.__init__

        def patched_init(self, config, *args, **kwargs):
            original_init(self, config, *args, **kwargs)
            self.quic_config.ssl_groups = TLS.groups

        hypercorn_quic.QuicProtocol.__init__ = patched_init

    def set_statsd_logger_class(self, statsd_logger) -> None:
        super().set_statsd_logger_class(statsd_logger)
        if self.needs_quic_patch:
            self.patch_quic_ssl_groups()

async def main():
    config = HypercornConfig()
    config.workers = 4
    config.worker_class = "uvloop"
    config.application_path = "nercone_dev.website.app:app"
    config.include_server_header = False
    config.keep_alive_timeout = 65
    config.alpn_protocols = ["h3", "h2", "http/1.1"]

    if os.path.exists(TLS.certfile) and os.path.exists(TLS.keyfile):
        config.certfile = TLS.certfile
        config.keyfile = TLS.keyfile
        config.ciphers = TLS.ciphers
        config.bind = Ports.https
        config.quic_bind = Ports.https
        config.insecure_bind = Ports.http
        config.alt_svc_headers = ['h3=":443"; ma=86400']
        config.needs_quic_patch = True
    else:
        config.bind = Ports.http

    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()
    sigint = signal.getsignal(signal.SIGINT)
    sigterm = signal.getsignal(signal.SIGTERM)
    loop.add_signal_handler(signal.SIGINT, shutdown_event.set)
    loop.add_signal_handler(signal.SIGTERM, shutdown_event.set)

    proc = multiprocessing.Process(target=run, args=[config])
    proc.start()

    try:
        while proc.is_alive() and not shutdown_event.is_set():
            await asyncio.sleep(0.1)
    finally:
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGTERM)
        signal.signal(signal.SIGINT, sigint)
        signal.signal(signal.SIGTERM, sigterm)

        if proc.is_alive():
            proc.terminate()
            while proc.is_alive():
                await asyncio.sleep(0.1)

        proc.join()
