import os
import ssl
import ctypes
import ctypes.util
from fourword.lib import FourWord
from hypercorn.run import run
from hypercorn.config import Config
from importlib.metadata import version

from .logger import Logger
from .constants import Repository, Ports, TLS
from .databases import MimeTypes

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

def main():
    startup_id = FourWord().compact_text
    Logger.log(f"[{startup_id}] nercone.dev ({Repository.version})")
    Logger.log(f"{' ' * (len(startup_id) + 2)} with hypercorn {version('hypercorn')}")
    Logger.log(f"{' ' * (len(startup_id) + 2)}      fastapi   {version('fastapi')}")
    Logger.log(f"{' ' * (len(startup_id) + 2)}      jinja2    {version('jinja2')}")
    Logger.log(f"{' ' * (len(startup_id) + 2)}      aioquic   {version('aioquic')}")
    Logger.log(f"{' ' * (len(startup_id) + 2)}      fourword  {version('fourword')}")
    Logger.log(f"{' ' * (len(startup_id) + 2)}      openssl   {ssl.OPENSSL_VERSION}")

    MimeTypes.fetch()

    config = HypercornConfig()
    config.application_path = "nercone_website.app:app"
    config.workers = 4
    config.worker_class = "uvloop"
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
        config.patch_quic_ssl_groups()
    else:
        config.bind = Ports.http

    run(config)

    Logger.log(f"[{startup_id}] STOP")

if __name__ == "__main__":
    main()
