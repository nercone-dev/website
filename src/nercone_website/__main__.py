import os
import socket
import uvicorn

from .databases import MimeTypes
from .constants import Ports

def main():
    MimeTypes.fetch()

    sockets = []

    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp.bind(("127.0.0.1" if Ports.uds else "0.0.0.0", Ports.tcp))
    sockets.append(tcp)

    if Ports.uds:
        os.umask(0o000)
        uds = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        uds.bind(Ports.uds)
        sockets.append(uds)

    uvicorn.run("nercone_website.app:app", sockets=sockets, workers=4, server_header=False)

if __name__ == "__main__":
    main()
