import os
import argparse
from typing import List

def main():
    parser = argparse.ArgumentParser(prog="nercone-website")
    parser.add_argument("command", nargs="?", choices=["dev"])
    args = parser.parse_args()

    if args.command == "dev":
        os.environ["WEBSITE_DEV"] = "1"

    from aki import Server, Listener, IPVersion

    from .app import app
    from .logger import logger_main
    from .databases import MimeTypes
    from .constants import Startup, Repository, Ports

    logger_main.log(f"[STARTED] ID={Startup.id.text} MODE={'DEV' if Startup.dev else 'PRODUCTION'} nercone.dev ({Repository.version})")

    MimeTypes.fetch()

    if args.command == "dev":
        Server(handler=app).run([Listener(IPVersion.IPv4, Ports.tcp)], workers=0)
        return

    listeners: List[Listener] = [Listener(ip_version=IPVersion.IPv4, port=Ports.tcp)] + ([Listener(path=Ports.uds)] if Ports.uds else [])

    Server(handler=app).run(listeners, workers=4)

    logger_main.log(f"[STOPPED] ID={Startup.id.text} MODE={'DEV' if Startup.dev else 'PRODUCTION'} nercone.dev ({Repository.version})")

if __name__ == "__main__":
    main()
