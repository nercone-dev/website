import json
import fcntl
from pathlib import Path
from fourword.lib import FourWord
from fastapi import Request, Response

from .constants import Files

def format_access(request: Request, response: Response | None = None) -> dict:
    return {
        "id": request.scope["nercone.dev"]["id"].text,
        "url": str(request.url),
        "status": response.status_code if response is not None else 0,
        "method": request.method,
        "client": {
            "host": request.scope["nercone.dev"]["network"].host,
            "port": request.scope["nercone.dev"]["network"].port
        },
        "headers": {
            "request": dict(request.headers),
            "response": dict(response.headers) if response is not None else {}
        },
        "managers": {
            "cc": request.scope["nercone.dev"]["cc"].directives,
            "pp": request.scope["nercone.dev"]["pp"].directives,
            "csp": request.scope["nercone.dev"]["csp"].directives,
            "timings": request.scope["nercone.dev"]["timings"].timings,
            "network": {"trusted": request.scope["nercone.dev"]["network"].trusted}
        }
    }

class Logger:
    @staticmethod
    def log(id: FourWord, contents: str = "", path: Path = Files.Logs.app):
        with path.open("a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            prefix = f"[{id.compact_text}]"
            f.write(f"{prefix} " + f"\n{' ' * (len(prefix) + 1)}".join(contents.split("\n")) + "\n")

    @staticmethod
    def log_access(id: FourWord, request: Request, response: Response | None = None, status_code: int | None = None):
        Logger.log(id, json.dumps(format_access(request, response)), path=Files.Logs.access)
        Logger.log(id, f"STATUS {response.status_code if response is not None else status_code or '---'} FROM {request.scope['nercone.dev']['network'].host}:{request.scope['nercone.dev']['network'].port} TO {str(request.url)}")

    @staticmethod
    def log_error(id: FourWord, traceback: str):
        Logger.log(id, traceback, path=Files.Logs.error)

    @staticmethod
    def log_report(id: FourWord, request: Request, body: dict | list, report_type: str):
        Logger.log(id, json.dumps({"report": {"type": report_type, "body": body}}), path=Files.Logs.report)
        Logger.log(id, f"{report_type} REPORT FROM {request.scope['nercone.dev']['network'].host}:{request.scope['nercone.dev']['network'].port} TO {str(request.url)}")
