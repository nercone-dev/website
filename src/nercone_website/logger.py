import json
from typing import Optional, Union

from aki import Request, Message
from modern import Logger, LogLevel
from fourword import FourWord

from .constants import Files

logger_main = Logger("website", filepath=Files.Logs.main)
logger_error = Logger("website", filepath=Files.Logs.error)
logger_access = Logger("website", filepath=Files.Logs.access)
logger_reports = Logger("website", filepath=Files.Logs.reports)
logger_warnings = Logger("website", filepath=Files.Logs.warnings)

def format_access(request: Request, response: Optional[Message] = None) -> dict:
    return {
        "id": request.scope["id"].text,
        "url": str(request.scope["url"]),
        "status": response.status_code if response is not None else 0,
        "method": request.method.as_str(),
        "client": {
            "host": request.scope["network"].host,
            "port": request.scope["network"].port
        },
        "headers": {
            "request": dict(request.headers.fields()),
            "response": dict(response.headers.fields()) if response is not None else {}
        },
        "managers": {
            "cc": request.scope["cc"].directives,
            "pp": request.scope["pp"].directives,
            "csp": request.scope["csp"].directives,
            "timings": request.scope["timings"].timings,
            "network": {"trusted": request.scope["network"].trusted}
        }
    }

def log_access(request: Request, response: Optional[Message] = None, status_code: Optional[int] = None):
    status_code = response.status_code if response is not None else status_code
    logger_main.log(f"{request.scope['id'].compact_text} STATUS {status_code or '---'} FROM {request.scope['network'].host}:{request.scope['network'].port} TO {str(request.scope['url'])}", level=LogLevel.INFO if (status_code or 500) < 400 else LogLevel.WARNING)
    logger_access.log(json.dumps(format_access(request, response)))

def log_report(request: Request, body: Union[dict, list], report_type: str):
    logger_warnings.log(f"{request.scope['id'].compact_text} REPORT {report_type} FROM {request.scope['network'].host}:{request.scope['network'].port}", level=LogLevel.WARNING)
    logger_reports.log(json.dumps(format_access(request) | {"report": body}), level=LogLevel.WARNING)

def log_error(id: FourWord, traceback: str):
    logger_error.log(f"{id.compact_text} An exception occurred on processing request:\n" + traceback, level=LogLevel.ERROR)
