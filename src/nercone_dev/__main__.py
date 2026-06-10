import ssl
import asyncio
from fourword.lib import FourWord
from importlib.metadata import version

from .logger import Logger
from .constants import Repository
from .website.__main__ import main as website_main

def main():
    startup_id = FourWord()
    startup_log = f"""
nercone.dev    {Repository.version}
with hypercorn {version('hypercorn')}
     fastapi   {version('fastapi')}
     jinja2    {version('jinja2')}
     fourword  {version('fourword')}
     openssl   {ssl.OPENSSL_VERSION}
    """
    Logger.log(startup_id, startup_log.strip())

    asyncio.run(website_main())

    Logger.log(startup_id, "STOPPED")

if __name__ == "__main__":
    main()
