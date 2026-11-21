import json
from fastapi import FastAPI, Request, Response

from ..logger import log_report

def add_report_route(app: FastAPI, path: str, report_type: str) -> None:
    async def report_route(request: Request) -> Response:
        content_type = request.headers.get("content-type", "")

        if "application/reports+json" not in content_type and "application/csp-report" not in content_type:
            return Response(status_code=415)

        try:
            data = json.loads(await request.body())
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return Response(status_code=400)

        if not isinstance(data, (dict, list)):
            return Response(status_code=400)

        log_report(request, data, report_type)
        return Response(status_code=204)

    app.add_route(path=path, route=report_route, methods=["POST"])
