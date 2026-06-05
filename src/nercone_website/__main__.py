import os
import ssl
import ctypes
import ctypes.util
from fourword.lib import FourWord
from hypercorn.run import run
from hypercorn.config import Config
from importlib.metadata import version

from .logger import Logger
from .constants import Repositories, Ports, TLS
from .databases import MimeTypes

def set_ssl_groups(context: ssl.SSLContext, groups: str) -> None:
    libssl_name = ctypes.util.find_library("ssl")
    if not libssl_name:
        raise ssl.SSLError("libssl Not Found")
    libssl = ctypes.CDLL(libssl_name)
    fn = libssl.SSL_CTX_set1_groups_list
    fn.restype = ctypes.c_int
    fn.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    ptr_size = ctypes.sizeof(ctypes.c_void_p)
    raw_ctx = ctypes.c_void_p.from_address(id(context) + 2 * ptr_size).value
    if fn(raw_ctx, groups.encode()) != 1:
        raise ssl.SSLError(f"SSL_CTX_set1_groups_list Failed: {groups!r}")

class HypercornConfig(Config):
    def create_ssl_context(self) -> ssl.SSLContext | None:
        context = super().create_ssl_context()
        if context is not None:
            context.options |= ssl.OP_NO_TICKET
            set_ssl_groups(context, TLS.groups)
        return context

def main():
    Logger.log(f"[{FourWord().compact_text}] ------- STARTUP")
    Logger.log(f"                                                           Nercone Website {Repositories.Server.version}+{Repositories.Contents.version}")
    Logger.log(f"                                                           Hypercorn {version('hypercorn')}")
    Logger.log(f"                                                           OpenSSL {ssl.OPENSSL_VERSION}")
    Logger.log()

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
    else:
        config.bind = Ports.http

    run(config)

if __name__ == "__main__":
    main()
