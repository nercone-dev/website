import uuid
import json
from pathlib import Path
from starlette.types import Scope
from datetime import datetime, timezone

access_log_path = Path.cwd().joinpath("logs", "access.log")
access_log_path.parent.mkdir(parents=True, exist_ok=True)

def log_access(scope: Scope, write: bool = False):
    client = scope.get("client") or ("", 0)
    server = scope.get("server") or ("", 0)
    headers = dict(scope.get("headers", []))
    hostname = headers.get(b"host", b"").decode().split(":")[0].strip()
    log = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from": {
            "address": client[0],
            "port": client[1]
        },
        "to": {
            "scheme": scope.get("scheme", "https"),
            "host": hostname,
            "port": server[1]
        },
        "method": scope.get("method", "GET"),
        "path": scope.get("path", "/"),
        "headers": {k.decode(): v.decode() for k, v in headers.items()}
    }
    if write:
        with access_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")
    return log

def finalize_log(log: dict, status_code: int, write: bool = True) -> None:
    log["status_code"] = status_code
    if write:
        with access_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")
    return log
