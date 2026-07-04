import os
import argparse

from aki import Server, Listener, IPVersion

from .app import app
from .databases import MimeTypes
from .constants import Ports

def main():
    parser = argparse.ArgumentParser(prog="nercone-website")
    parser.add_argument("command", nargs="?", choices=["dev"])
    args = parser.parse_args()

    MimeTypes.fetch()

    if args.command == "dev":
        os.environ["WEBSITE_DEV"] = "1"
        Server(handler=app).run([Listener(IPVersion.IPv4, Ports.tcp)], workers=0)
        return

    listeners: list[Listener] = [Listener(ip_version=IPVersion.IPv4, port=Ports.tcp)] + ([Listener(path=Ports.uds)] if Ports.uds else [])

    Server(handler=app).run(listeners, workers=4)

if __name__ == "__main__":
    main()
