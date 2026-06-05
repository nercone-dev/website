import os
import ssl
from fourword.lib import FourWord
from hypercorn.run import run
from hypercorn.config import Config
from importlib.metadata import version

from .logger import Logger
from .constants import Repositories, Ports, TLS
from .databases import MimeTypes

class HypercornConfig(Config):
    def create_ssl_context(self) -> ssl.SSLContext | None:
        context = super().create_ssl_context()
        if context is not None:
            context.options |= ssl.OP_NO_TICKET
        return context

def main():
    Logger.log(f"[{FourWord().compact_text}] ------- STARTUP")
    Logger.log(f"                            Nercone Website {Repositories.Server.version}+{Repositories.Contents.version}")
    Logger.log(f"                            Hypercorn {version('hypercorn')}")
    Logger.log(f"                            OpenSSL {ssl.OPENSSL_VERSION}")
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
