import asyncio
from nercone_modern import Logging

from .constants import Files, Repository
from .databases import MimeTypes
from .website.__main__ import main as website_main

def main():
    logger = Logging("nercone.dev", filepath=Files.Logs.main)
    logger.log(f"STARTED nercone.dev ({Repository.version})")

    MimeTypes.fetch()

    try:
        asyncio.run(website_main())
    except KeyboardInterrupt:
        pass

    logger.log("STOPPED")

if __name__ == "__main__":
    main()
