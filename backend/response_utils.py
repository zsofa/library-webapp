from typing import Any, Dict, Optional, Tuple

from flask import Response, g, jsonify, make_response


def error_response(
    error_code: str,
    message: Optional[str] = None,
    status: int = 400,
    details: Optional[Any] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """
    Build a standardized JSON error payload.

    Base format:
    {
      "error": "<short_code>",
      "message": "<human readable>",
      "details": ... (optional, arbitrary structure),
      "meta": { ... } (optional key/value pairs; auto-includes request_id if available)
    }
    """
    payload: Dict[str, Any] = {"error": error_code}
    if message:
        payload["message"] = message
    if details is not None:
        payload["details"] = details

    # Auto-inject request_id into meta if present in flask.g
    merged_meta: Dict[str, Any] = {}
    if isinstance(meta, dict):
        merged_meta.update(meta)
    req_id = getattr(g, "request_id", None)
    if req_id and "request_id" not in merged_meta:
        merged_meta["request_id"] = req_id
    if merged_meta:
        payload["meta"] = merged_meta

    resp = make_response(jsonify(payload), status)
    return resp, status


def unauthorized(message: str = "Missing or invalid token.") -> Tuple[Response, int]:
    return error_response("unauthorized", message, status=401)


def forbidden(message: str = "Insufficient permissions.") -> Tuple[Response, int]:
    return error_response("forbidden", message, status=403)


def not_found(message: str = "Resource not found.") -> Tuple[Response, int]:
    return error_response("not_found", message, status=404)


def conflict(message: str = "Conflict.") -> Tuple[Response, int]:
    return error_response("conflict", message, status=409)


def server_error(message: str = "Unexpected server error.") -> Tuple[Response, int]:
    return error_response("server_error", message, status=500)
