import json
from fastapi import FastAPI, Request, Response
from ..logger import Logger

def add_report_route(app: FastAPI, path: str, report_type: str):
    async def report_route(request: Request) -> Response:
        content_type = request.headers.get("content-type", "")

        if "application/reports+json" not in content_type and "application/csp-report" not in content_type:
            return Response(status_code=415)

        body = await request.body()
        max_bytes = 65536

        if len(body) > max_bytes:
            return Response(status_code=413)

        try:
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return Response(status_code=400)

        if not isinstance(data, (dict, list)):
            return Response(status_code=400)

        Logger.log_report(request.scope["nercone.dev"]["id"], request, data, report_type)
        return Response(status_code=204)

    app.add_api_route(path=path, name=f"report_{report_type.lower()}", methods=["POST"], endpoint=report_route)
