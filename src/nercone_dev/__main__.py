import asyncio
import logging
import logging.handlers
import multiprocessing
from fourword.lib import FourWord
from rich.logging import RichHandler

from .constants import Directories, Repository
from .website.__main__ import main as website_main

def main():
    id = FourWord()

    queue = multiprocessing.Queue()

    file_handler = logging.FileHandler(Directories.logs.joinpath(f"{id.readable_text}.log"))
    file_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    listener = logging.handlers.QueueListener(queue, RichHandler(), file_handler, respect_handler_level=True)
    listener.start()

    queue_handler = logging.handlers.QueueHandler(queue)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(queue_handler)

    logger = logging.getLogger("nercone_dev")
    logger.info(f"nercone.dev ({Repository.version})")

    try:
        asyncio.run(website_main(queue))
    except KeyboardInterrupt:
        pass

    logger.info("STOPPED")
    listener.stop()

if __name__ == "__main__":
    main()
