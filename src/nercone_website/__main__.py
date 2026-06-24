import os
import socket
import uvicorn
from uvicorn.supervisors import Multiprocess

from .databases import MimeTypes
from .constants import Ports

def main():
    MimeTypes.fetch()

    sockets = []

    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp.bind(("127.0.0.1" if Ports.uds else "0.0.0.0", Ports.tcp))
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

    config = uvicorn.Config("nercone_website.app:app", workers=4, server_header=False)
    server = uvicorn.Server(config)
    Multiprocess(config, target=server.run, sockets=sockets).run()

if __name__ == "__main__":
    main()
