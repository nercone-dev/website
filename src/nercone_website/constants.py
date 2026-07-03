import os
import subprocess
import http.cookies
from pathlib import Path
from fourword.lib import FourWord

reserved_cookie_keys = frozenset(http.cookies.Morsel._reserved)

class Startup:
    id = FourWord(os.environ.setdefault("WEBSITE_ID", os.environ.get("WEBSITE_ID", FourWord().text)))
    dev = os.environ.get("WEBSITE_DEV") == "1"

class Directories:
    base = Path.cwd()
    logs = base.joinpath("logs")
    public = base.joinpath("public")
    databases = base.joinpath("databases")

class Files:
    mime_types = Directories.databases.joinpath("mime.types")
    access_counter = Directories.databases.joinpath("access_counter.txt")

    class Logs:
        main = Directories.logs.joinpath("main.log")
        error = Directories.logs.joinpath("error.log")
        access = Directories.logs.joinpath("access.log")
        reports = Directories.logs.joinpath("reports.log")
        warnings = Directories.logs.joinpath("warnings.log")

class Repository:
    url = subprocess.run(["/usr/bin/git", "remote", "get-url", "origin"], text=True, capture_output=True, cwd=Directories.base).stdout.strip()
    version = subprocess.run(["/usr/bin/git", "rev-parse", "--short", "HEAD"], text=True, capture_output=True, cwd=Directories.base).stdout.strip()

class Hostnames:
    public = ["nercone.dev", "nerc1.dev", "diamondgotcat.net", "d-g-c.net"]
    local = ["localhost", "127.0.0.1"]
    all = local + public

class Ports:
    tcp = int(os.environ.get("WEBSITE_TCP", "8080"))
    uds = os.environ.get("WEBSITE_UDS")
