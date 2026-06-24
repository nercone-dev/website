import os
import subprocess
import http.cookies
from pathlib import Path
from fourword.lib import FourWord

startup_id = FourWord(os.environ.setdefault("STARTUP_ID", FourWord().text))
unix_socket = os.environ.get("WEBSITE_UDS")
reserved_cookie_keys = frozenset(http.cookies.Morsel._reserved)

class Directories:
    base = Path.cwd()
    public = base.joinpath("public")
    logs = base.joinpath("logs")
    databases = base.joinpath("databases")

class Files:
    mime_types = Directories.databases.joinpath("mime.types")
    access_counter = Directories.databases.joinpath("access_counter.txt")

    class Logs:
        main = Directories.logs.joinpath(startup_id.readable_text + ".log")
        error = Directories.logs.joinpath(startup_id.readable_text+ "-error.log")
        access = Directories.logs.joinpath(startup_id.readable_text + "-access.log")
        reports = Directories.logs.joinpath(startup_id.readable_text + "-reports.log")
        warnings = Directories.logs.joinpath(startup_id.readable_text + "-warnings.log")

class Repository:
    url = subprocess.run(["/usr/bin/git", "remote", "get-url", "origin"], text=True, capture_output=True, cwd=Directories.base).stdout.strip()
    version = subprocess.run(["/usr/bin/git", "rev-parse", "--short", "HEAD"], text=True, capture_output=True, cwd=Directories.base).stdout.strip()

class Hostnames:
    public = ["nercone.dev", "nerc1.dev", "diamondgotcat.net", "d-g-c.net"]
    local = ["localhost", "127.0.0.1"]
    all = local + public
