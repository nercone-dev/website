import os
import subprocess
from enum import Enum
from typing import Optional
from pathlib import Path
from fwid import FWID

class StartupMode(Enum):
    PRODUCTION = "Production"
    DEVELOPMENT = "Development"

class Startup:
    id: FWID = FWID()
    mode: StartupMode = StartupMode.DEVELOPMENT if os.environ.get("WEBSITE_DEV") == "1" else StartupMode.PRODUCTION
    version: str = os.environ.get("WEBSITE_VERSION") or (subprocess.run(["/usr/bin/git", "rev-parse", "--short", "HEAD"], text=True, capture_output=True, cwd=Path.cwd()).stdout.strip() if Path("/usr/bin/git").exists() else "unknown")

class Directories:
    base = Path.cwd()

    public = base.joinpath("public")
    static    = public.joinpath("static")
    templates = public.joinpath("templates")

    assets = static.joinpath("assets")

    private = base.joinpath("private")
    logs      = private.joinpath("logs")
    databases = private.joinpath("databases")

class Files:
    mime_types = Directories.databases.joinpath("mime.types")
    access_counter = Directories.databases.joinpath("access_counter.txt")

    class Bundles:
        css_entry  = Directories.assets.joinpath("styles", "index.css")
        css_output = Directories.assets.joinpath("style.css")
        js_entry   = Directories.assets.joinpath("scripts", "index.js")
        js_output  = Directories.assets.joinpath("script.js")
        themes     = sorted(Directories.assets.joinpath("styles", "themes").glob("*.css"))

    class Fonts:
        ttf   = list(Directories.assets.joinpath("fonts").glob("*/*.ttf"))
        woff2 = list(Directories.assets.joinpath("fonts").glob("*/*.woff2"))
        all   = ttf + woff2

    class Logs:
        main = Directories.logs.joinpath("main.log")
        access = Directories.logs.joinpath("access.log")
        error = Directories.logs.joinpath("error.log")
        report = Directories.logs.joinpath("report.log")

class Hostnames:
    public = ["nerc1.dev", "nercone.dev", "d-g-c.net", "diamondgotcat.net", "umineco.dev"]
    local = ["localhost", "127.0.0.1"]
    all = local + public

    @classmethod
    def matches(cls, hostname: str) -> bool:
        return any(hostname == candidate or hostname.endswith("." + candidate) for candidate in cls.all)

class Ports:
    tcp_host: str = os.environ.get("WEBSITE_TCP_HOST", "0.0.0.0")
    tcp_port: int = int(os.environ.get("WEBSITE_TCP_PORT", "8080"))
    uds: Optional[str] = os.environ.get("WEBSITE_UDS")
