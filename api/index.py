"""
Vercel Python Function entrypoint.

A thin FastAPI adapter that turns each /api/* request into the API
Gateway-style event the existing Lambda handlers expect, calls the handler
unchanged, and converts its {statusCode, headers, body} result back into an
HTTP response.
"""
import hmac
import json
import os
import re
import sys
from pathlib import Path

# Make `backend.*` importable regardless of the function's working directory
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.concurrency import run_in_threadpool  # noqa: E402
from fastapi.responses import Response  # noqa: E402

from backend.shared.auth import AuthError, verify_token  # noqa: E402
from backend.shared.logging import get_logger  # noqa: E402
from backend.shared.response import response as lambda_response  # noqa: E402
from backend.lambdas.meals.handler import handler as meals_handler  # noqa: E402
from backend.lambdas.meal_logs.handler import handler as meal_logs_handler  # noqa: E402
from backend.lambdas.summary.handler import handler as summary_handler  # noqa: E402
from backend.lambdas.users.handler import handler as users_handler  # noqa: E402
from backend.lambdas.daily_summaries_batch.handler import handler as daily_summaries_batch_handler  # noqa: E402

logger = get_logger(__name__)

CRON_PATH = "/cron/daily-summaries"

# The nine API Gateway resource templates and the handler that serves each
RESOURCES = [
    ("/ingredients", meals_handler),
    ("/ingredients/{id}", meals_handler),
    ("/meals", meals_handler),
    ("/meals/{id}", meals_handler),
    ("/meal-logs", meal_logs_handler),
    ("/meal-logs/{id}", meal_logs_handler),
    ("/daily-summary", summary_handler),
    ("/users/bootstrap", users_handler),
    ("/users/me", users_handler),
]


def _compile(template):
    pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", template)
    return re.compile(f"^{pattern}$")


_ROUTES = [(template, _compile(template), handler) for template, handler in RESOURCES]


def match_resource(path):
    """Return (template, path_parameters, handler) for a path, or None."""
    for template, regex, handler in _ROUTES:
        m = regex.match(path)
        if m:
            return template, m.groupdict(), handler
    return None


def _normalize_path(full_path):
    # Vercel forwards the original /api/... path; strip the prefix and any trailing slash
    path = "/" + full_path.strip("/")
    if path == "/api" or path.startswith("/api/"):
        path = path[len("/api"):] or "/"
    return path


def _to_response(result):
    return Response(
        content=result.get("body") or "",
        status_code=result.get("statusCode", 200),
        headers=result.get("headers") or {},
    )


def _error(status_code, message):
    return _to_response(lambda_response(status_code, {"error": message}))


def _bearer_token(request):
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def build_event(request, template, path_parameters, body, claims):
    return {
        "httpMethod": request.method,
        "resource": template,
        "path": request.url.path,
        "pathParameters": path_parameters or None,
        "queryStringParameters": dict(request.query_params) or None,
        "headers": dict(request.headers),
        "body": body,
        "isBase64Encoded": False,
        "requestContext": {
            "authorizer": {
                "claims": claims,
            },
        },
    }


def _run_daily_summaries(request):
    secret = os.environ.get("CRON_SECRET")
    token = _bearer_token(request)
    if not secret or not token or not hmac.compare_digest(token, secret):
        return _error(401, "Unauthorized")

    result = daily_summaries_batch_handler({}, None)
    status_code = result.get("statusCode", 500)
    return _to_response(lambda_response(status_code, result.get("metrics", {})))


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def dispatch(full_path: str, request: Request):
    path = _normalize_path(full_path)

    if path == CRON_PATH:
        if request.method != "GET":
            return _error(405, "Method Not Allowed")
        return await run_in_threadpool(_run_daily_summaries, request)

    matched = match_resource(path)
    if matched is None:
        return _error(404, "Not Found")
    template, path_parameters, handler = matched

    # CORS preflight carries no Authorization header
    if request.method == "OPTIONS":
        return _to_response(lambda_response(204, None))

    token = _bearer_token(request)
    if token is None:
        return _error(401, "Unauthorized")
    try:
        claims = verify_token(token)
    except AuthError as exc:
        logger.info("Rejected token", extra={"reason": str(exc)})
        return _error(401, "Unauthorized")

    raw_body = await request.body()
    body = raw_body.decode("utf-8") if raw_body else None
    event = build_event(request, template, path_parameters, body, claims)

    try:
        result = await run_in_threadpool(handler, event, None)
    except Exception:
        # Handlers log and re-raise; API Gateway would have returned a 502 here
        logger.exception("Unhandled handler error", extra={"resource": template, "method": request.method})
        return _error(500, "Internal Server Error")

    return _to_response(result)
