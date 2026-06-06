import os
import subprocess
import http.cookies
from pathlib import Path

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
        app = Directories.logs.joinpath("app.log")
        access = Directories.logs.joinpath("access.log")
        error = Directories.logs.joinpath("error.log")

class Repositories:
    class Server:
        url = subprocess.run(["/usr/bin/git", "remote", "get-url", "origin"], text=True, capture_output=True, cwd=Directories.base).stdout.strip()
        version = subprocess.run(["/usr/bin/git", "rev-parse", "--short", "HEAD"], text=True, capture_output=True, cwd=Directories.base).stdout.strip()

    class Contents:
        url = subprocess.run(["/usr/bin/git", "remote", "get-url", "origin"], text=True, capture_output=True, cwd=Directories.public).stdout.strip()
        version = subprocess.run(["/usr/bin/git", "rev-parse", "--short", "HEAD"], text=True, capture_output=True, cwd=Directories.public).stdout.strip()

class Hostnames:
    public = ["nercone.dev", "nerc1.dev", "diamondgotcat.net", "d-g-c.net"]
    local = ["localhost", "127.0.0.1"]
    all = local + public

class Ports:
    http = ["0.0.0.0:80", "[::]:80"]
    https = ["0.0.0.0:443", "[::]:443"]

class TLS:
    certfile = os.environ.get("WEBSITE_TLS_CERTFILE", "/etc/letsencrypt/live/nercone.dev/fullchain.pem")
    keyfile = os.environ.get("WEBSITE_TLS_KEYFILE", "/etc/letsencrypt/live/nercone.dev/privkey.pem")
    ciphers = "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305"
    groups = "X25519MLKEM768:SecP384r1MLKEM1024:SecP256r1MLKEM768:MLKEM1024:MLKEM768:X25519:prime256v1:secp384r1"
