import json
from fwid import FWID
from pathlib import Path
from typing import Optional, Union
from fastapi import Request, Response

from .constants import Files

def format_access(request: Request, response: Optional[Response] = None) -> dict:
    return {
        "request": {
            "id": request.scope["nercone"]["request"]["id"].text(),
            "url": str(request.scope["nercone"]["request"]["url"]),
            "method": request.method,
            "client": {
                "host": None if request.client is None else request.client.host,
                "port": None if request.client is None else request.client.port,
            },
            "headers": [[key.decode("latin-1"), value.decode("latin-1")] for key, value in request.headers.raw]
        },
        "response": {
            "status": response.status_code,
            "headers": [[key.decode("latin-1"), value.decode("latin-1")] for key, value in response.headers.raw],
        } if response is not None else {}
    }

def format_error(id: FWID, traceback: str) -> dict:
    return {
        "id": id.text(),
        "traceback": traceback,
    }

def format_report(request: Request, data: Union[dict,list], report_type: str) -> dict:
    return {
        "id": request.scope["nercone"]["request"]["id"].text(),
        "type": report_type,
        "data": data,
    }

def format_client(request: Request) -> str:
    if request.client is None:
        return "---:---"
    return f"{request.client.host}:{request.client.port}"

def append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(line + "\n")

def log_main(content: str) -> None:
    append_line(Files.Logs.main, content)

def log_access(request: Request, response: Optional[Response] = None) -> None:
    request_id = request.scope["nercone"]["request"]["id"].readable_text
    status = (response.status_code if response is not None else None) or "---"
    log_main(f"{request_id} STATUS {status} FROM {format_client(request)} TO {request.scope['nercone']['request']['url']}")
    append_line(Files.Logs.access, json.dumps(format_access(request, response)))

def log_error(id: FWID, traceback: str) -> None:
    log_main(f"ERROR ID={id.text()}")
    append_line(Files.Logs.error, json.dumps(format_error(id, traceback)))

def log_report(request: Request, data: Union[dict,list], report_type: str) -> None:
    request_id = request.scope["nercone"]["request"]["id"].readable_text
    log_main(f"{request_id} {report_type} REPORT FROM {format_client(request)} TO {request.scope['nercone']['request']['url']}")
    append_line(Files.Logs.report, json.dumps(format_report(request, data, report_type)))
