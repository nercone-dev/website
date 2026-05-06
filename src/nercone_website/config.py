import subprocess
from pathlib import Path

VERSION = subprocess.run(["/usr/bin/git", "rev-parse", "HEAD"], text=True, capture_output=True).stdout.strip()

class Hostnames:
    normal = ["localhost", "nercone.dev", "nerc1.dev", "diamondgotcat.net", "d-g-c.net"]
    onion = "4sbb7xhdn4meuesnqvcreewk6sjnvchrsx4lpnxmnjhz2soat74finid.onion"
    all = normal + [onion]

class Directories:
    base = Path.cwd()
    public = base.joinpath("public")
    logs = base.joinpath("logs")
    databases = base.joinpath("databases")

class Files:
    quotes = Directories.public.joinpath("quotes.txt")
    shorturls = Directories.public.joinpath("shorturls.json")

    class Logs:
        uvicorn = Directories.logs.joinpath("uvicorn.log")
        access = Directories.logs.joinpath("access.log")

    class Databases:
        access_counter = Directories.databases.joinpath("access_counter.db")
