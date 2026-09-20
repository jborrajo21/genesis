import base64
import binascii
import io
import json
import logging
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from genesis.errors import GenesisError
from genesis.planner import _parse_plan
from genesis.scaffolder import normalize, scaffold

Response = dict[str, Any]

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    headers: dict[str, str]
    body: str


def _normalise(event: dict[str, Any]) -> Request:
    """Raw payload-format-2.0 event -> Request. The only place base64 decoding happens."""
    method = event["requestContext"]["http"]["method"]
    raw_path = event["rawPath"]
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    body = event.get("body") or ""
    if event.get("isBase64Encoded", False):
        body = base64.b64decode(body).decode("utf-8")

    return Request(method=method, path=raw_path, headers=headers, body=body)


def _json(status: int, payload: dict[str, Any], headers: dict[str, str] | None = None) -> Response:
    """Build a JSON response, merging any caller headers over the content type."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **(headers or {})},
        "body": json.dumps(payload),
    }


def _binary(
    status: int,
    data: bytes,
    content_type: str,
    headers: dict[str, str] | None = None,
) -> Response:
    """Build a binary response; the only place isBase64Encoded is set."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": content_type, **(headers or {})},
        "body": base64.b64encode(data).decode("ascii"),
        "isBase64Encoded": True,
    }


def _error(status: int, message: str, headers: dict[str, str] | None = None) -> Response:
    """Build an error response carrying a single actionable message."""
    return _json(status, {"message": message}, headers)


def _scaffold(req: Request) -> Response:
    """POST /scaffold — plan JSON in, repo as a zip out."""
    tmp = Path(tempfile.mkdtemp())
    try:
        plan = _parse_plan(json.loads(req.body))
        name = normalize(plan.project_name)
        repo = scaffold(plan, tmp / name)
        return _binary(
            200,
            _zip_dir(repo),
            "application/zip",
            {
                "Content-Disposition": f'attachment; filename="{name}.zip"',
                "Genesis-Supported": "true" if plan.supported else "false",
            },
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _zip_dir(root: Path) -> bytes:
    """Zip a directory in memory as one deterministic top-level folder."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(root.parent))
    return buf.getvalue()


def _plan(req: Request) -> Response:
    """POST /plan — BYOK. Task 3. Key from a header, never logged, never persisted."""
    return _error(501, "Planning is not available yet. Use POST /scaffold with a plan JSON.")


def _index(req: Request) -> Response:
    """GET / — Task 5. Until then, something better than a 404."""
    return _error(501, "Nothing here yet. POST a plan JSON to /scaffold.")


_ROUTES: dict[str, dict[str, Callable[[Request], Response]]] = {
    "/scaffold": {"POST": _scaffold},
    "/plan": {"POST": _plan},
    "/": {"GET": _index},
}


def _dispatch(req: Request) -> Response:
    """Route a request, distinguishing an unknown path (404) from a wrong method (405)."""
    methods = _ROUTES.get(req.path)
    if methods is None:
        return _error(404, f"No such path: {req.path}. Try GET / for the endpoint list.")
    route = methods.get(req.method)
    if route is None:
        allow = ", ".join(sorted(methods))
        return _error(
            405,
            f"{req.method} not allowed on {req.path}. Use {allow}.",
            {"Allow": allow},
        )
    return route(req)


def handler(event: dict[str, Any], context: Any) -> Response:
    """Lambda entry point: normalise, dispatch, and map exceptions to status codes."""
    try:
        return _dispatch(_normalise(event))
    except (json.JSONDecodeError, binascii.Error, UnicodeDecodeError) as e:
        return _error(400, f"Could not read the request body: {e}")
    except KeyError as e:
        return _error(400, f"Missing required key: {e}")
    except TypeError:
        _log.exception("TypeError while handling request")
        return _error(400, "Malformed request: expected a plan object.")
    except GenesisError as e:
        return _error(400, str(e))
    except OSError:
        _log.exception("Filesystem error while handling request")
        return _error(500, "Could not complete the request.")
    except Exception:
        _log.exception("Unhandled error while handling request")
        return _error(500, "Unexpected error.")
