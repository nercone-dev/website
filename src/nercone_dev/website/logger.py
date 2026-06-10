import json
from logging import Logger
from fourword.lib import FourWord
from fastapi import Request, Response

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

def log_access(logger: Logger, request: Request, response: Response | None = None, status_code: int | None = None):
    logger.info(f"Website: STATUS {response.status_code if response is not None else status_code or '---'} FROM {request.scope['nercone.dev']['network'].host}:{request.scope['nercone.dev']['network'].port} TO {str(request.url)}\n" + json.dumps(format_access(request, response)))

def log_error(id: FourWord, logger: Logger, traceback: str):
    logger.error(f"Website: An exception occurred on processing request (Request ID: {id.text}):\n" + traceback)

def log_report(id: FourWord, logger: Logger, request: Request, body: dict | list, report_type: str):
    logger.warning(f"Website: {report_type} Report Received (Request ID: {id.text}):\n" + json.dumps(format_access(request) | {"report": {"type": report_type, "body": body}}))
