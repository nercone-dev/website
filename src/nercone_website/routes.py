import json
from aki import Aki, Request, Message

from .logger import log_report

def add_report_route(app: Aki, path: str, report_type: str):
    async def report_route(request: Request) -> Message:
        content_type = request.header("content-type") or ""

        if "application/reports+json" not in content_type and "application/csp-report" not in content_type:
            return Message.response(415, request.version)

        try:
            data = json.loads(await request.body())
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return Message.response(400, request.version)

        if not isinstance(data, (dict, list)):
            return Message.response(400, request.version)

        log_report(request, data, report_type)
        return Message.response(204, request.version)

    app.add_route(path=path, methods=["POST"], callback=report_route)
