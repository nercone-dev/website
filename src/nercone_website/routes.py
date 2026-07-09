import json
from aki import Aki, Request, Response

from .logger import log_report

def add_report_route(app: Aki, path: str, report_type: str):
    async def report_route(request: Request) -> Response:
        content_type = request.headers.get("content-type", "")

        if "application/reports+json" not in content_type and "application/csp-report" not in content_type:
            return Response(415)

        try:
            data = request.json
        except (json.JSONDecodeError, ValueError):
            return Response(400)

        if not isinstance(data, (dict, list)):
            return Response(400)

        log_report(request, data, report_type)
        return Response(204)

    app.add_route(path=path, methods=["POST"], callback=report_route)
