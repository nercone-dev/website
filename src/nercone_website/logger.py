import json
from fastapi import Request, Response
from fourword.lib import FourWord
from nercone_modern.logging import Logging, LoggingLevel

from .constants import Files

logger_main = Logging("website", filepath=Files.Logs.main)
logger_error = Logging("website", filepath=Files.Logs.error)
logger_access = Logging("website", filepath=Files.Logs.access)
logger_reports = Logging("website", filepath=Files.Logs.reports)
logger_warnings = Logging("website", filepath=Files.Logs.warnings)

def format_access(request: Request, response: Response | None = None) -> dict:
    return {
        "id": request.scope["website"]["id"].text,
        "url": str(request.url),
        "status": response.status_code if response is not None else 0,
        "method": request.method,
        "client": {
            "host": request.scope["website"]["network"].host,
            "port": request.scope["website"]["network"].port
        },
        "headers": {
            "request": dict(request.headers),
            "response": dict(response.headers) if response is not None else {}
        },
        "managers": {
            "cc": request.scope["website"]["cc"].directives,
            "pp": request.scope["website"]["pp"].directives,
            "csp": request.scope["website"]["csp"].directives,
            "timings": request.scope["website"]["timings"].timings,
            "network": {"trusted": request.scope["website"]["network"].trusted}
        }
    }

def log_access(request: Request, response: Response | None = None, status_code: int | None = None):
    status_code = response.status_code if response is not None else status_code
    logger_main.log(f"{request.scope['website']['id'].compact_text} STATUS {status_code or '---'} FROM {request.scope['website']['network'].host}:{request.scope['website']['network'].port} TO {str(request.url)}", level=LoggingLevel.INFO if (status_code or 500) < 400 else LoggingLevel.WARNING)
    logger_access.log(json.dumps(format_access(request, response)))

def log_report(request: Request, body: dict | list, report_type: str):
    logger_warnings.log(f"{request.scope['website']['id'].compact_text} REPORT {report_type} FROM {request.scope['website']['network'].host}:{request.scope['website']['network'].port}", level=LoggingLevel.WARNING)
    logger_reports.log(json.dumps(format_access(request) | {"report": body}), level=LoggingLevel.WARNING)

def log_error(id: FourWord, traceback: str):
    logger_error.log(f"{id.compact_text} An exception occurred on processing request:\n" + traceback, level=LoggingLevel.ERROR)
