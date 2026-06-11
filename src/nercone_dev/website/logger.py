import json
from fastapi import Request, Response
from fourword.lib import FourWord
from nercone_modern.logging import Logging, LoggingLevel

from ..constants import Files

logger_main = Logging("website", filepath=Files.Logs.main)
logger_access = Logging("website", filepath=Files.Logs.access)
logger_reports = Logging("website", filepath=Files.Logs.reports)
logger_warnings = Logging("website", filepath=Files.Logs.warnings)
logger_error = Logging("website", filepath=Files.Logs.error)

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
    status_code = response.status_code if response is not None else status_code
    logger_main.log(f"{request.scope['nercone.dev']['id'].compact_text} STATUS {status_code or '---'} FROM {request.scope['nercone.dev']['network'].host}:{request.scope['nercone.dev']['network'].port} TO {str(request.url)}", level=LoggingLevel.INFO if (status_code or 500) < 400 else LoggingLevel.WARNING)
    logger_access.log(json.dumps(format_access(request, response)))

def log_report(request: Request, body: dict | list, report_type: str):
    logger_warnings.log(f"{request.scope['nercone.dev']['id'].compact_text} REPORT {report_type} FROM {request.scope['nercone.dev']['network'].host}:{request.scope['nercone.dev']['network'].port}", level=LoggingLevel.WARNING)
    logger_reports.log(json.dumps(format_access(request) | {"report": body}), level=LoggingLevel.WARNING)

def log_error(id: FourWord, traceback: str):
    logger_error.log(f"{id.compact_text} An exception occurred on processing request:\n" + traceback, level=LoggingLevel.ERROR)
