import json
from fourword.lib import FourWord
from nercone_modern import Logging
from fastapi import Request, Response

from ..constants import Files

logger_main = Logging("Website", filepath=Files.Logs.main)
logger_access = Logging("Website", filepath=Files.Logs.access)
logger_reports = Logging("Website", filepath=Files.Logs.reports)
logger_warnings = Logging("Website", filepath=Files.Logs.warnings)
logger_error = Logging("Website", filepath=Files.Logs.error)

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

def log_access(request: Request, response: Response | None = None, status_code: int | None = None):
    logger_main.log(f"STATUS {response.status_code if response is not None else status_code or '---'} FROM {request.scope['nercone.dev']['network'].host}:{request.scope['nercone.dev']['network'].port} TO {str(request.url)}")
    logger_access.log(json.dumps(format_access(request, response)))

def log_error(id: FourWord, traceback: str):
    logger_error.log(f"An exception occurred on processing request ({id.text}):\n" + traceback)

def log_report(id: FourWord, request: Request, body: dict | list, report_type: str):
    logger_warnings.log(f"{report_type} Report Received ({id.text})")
    logger_reports.log(f"{report_type} Report Received ({id.text}):\n" + json.dumps(format_access(request) | {"report": {"type": report_type, "body": body}}))
