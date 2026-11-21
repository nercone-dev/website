import os
import socket
import uvicorn
from uvicorn.supervisors import ChangeReload, Multiprocess

from .logger import log_main
from .helpers import MimeTypes
from .constants import Startup, StartupMode, Ports

def main() -> None:
    MimeTypes.fetch()

    log_main(f"[STARTED] ID={Startup.id.readable_text} MODE={Startup.mode.value} VERSION={Startup.version}")

    sockets = []

    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp.bind((Ports.tcp_host, Ports.tcp_port))
    tcp.set_inheritable(True)
    sockets.append(tcp)

    if Ports.uds:
        try:
            os.unlink(Ports.uds)
        except FileNotFoundError:
            pass
        os.umask(0o000)
        uds = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        uds.bind(Ports.uds)
        uds.set_inheritable(True)
        sockets.append(uds)

    if Startup.mode == StartupMode.DEVELOPMENT:
        config = uvicorn.Config("website.app:app", server_header=False, reload=True)
        ChangeReload(config, target=uvicorn.Server(config).run, sockets=sockets).run()
    else:
        config = uvicorn.Config("website.app:app", workers=4, server_header=False)
        Multiprocess(config, sockets=sockets).run()

if __name__ == "__main__":
    main()
