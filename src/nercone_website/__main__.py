import os
import stat
import signal
import asyncio
import argparse
from pathlib import Path
from typing import List

async def serve():
    from aki import Server, Port

    from .app import app
    from .logger import logger_main
    from .databases import MimeTypes
    from .constants import Startup, Repository, Ports

    logger_main.log(f"[STARTED] ID={Startup.id.text} MODE={'DEV' if Startup.dev else 'PRODUCTION'} nercone.dev ({Repository.version})")

    MimeTypes.fetch()

    server = Server()

    if Startup.dev:
        handle = await server.serve(app, [Port.TCP(Ports.tcp)], on_websocket=app.on_websocket)

    else:
        if Ports.uds:
            uds_path = Path(Ports.uds)

            if uds_path.exists() and stat.S_ISSOCK(uds_path.stat().st_mode):
                uds_path.unlink()

        listeners: List[Port] = [Port.TCP(Ports.tcp)] + ([Port.UDS(Ports.uds)] if Ports.uds else [])
        handle = await server.run(app, listeners, workers=4, on_websocket=app.on_websocket)

    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()

    for number in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(number, stopping.set)

    try:
        await stopping.wait()
    finally:
        await handle.close()

    logger_main.log(f"[STOPPED] ID={Startup.id.text} MODE={'DEV' if Startup.dev else 'PRODUCTION'} nercone.dev ({Repository.version})")

def main():
    parser = argparse.ArgumentParser(prog="nercone-website")
    parser.add_argument("command", nargs="?", choices=["dev"])
    args = parser.parse_args()

    if args.command == "dev":
        os.environ["WEBSITE_DEV"] = "1"

    asyncio.run(serve())

if __name__ == "__main__":
    main()
