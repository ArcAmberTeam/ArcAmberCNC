"""Version 1 only permits a service health query, never machine commands."""

import json

MAX_FRAME_BYTES = 65536


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def response(payload: bytes) -> bytes:
    request_id = ""
    code = "invalid_request"
    try:
        message = json.loads(
            payload, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
        if not isinstance(message, dict):
            raise ValueError
        candidate = message.get("request_id")
        if not isinstance(candidate, str) or not 1 <= len(candidate) <= 64:
            raise ValueError
        request_id = candidate
        if set(message) != {"version", "request_id", "method"}:
            raise ValueError
        if type(message["version"]) is not int or message["version"] != 1:
            code = "unsupported_version"
            raise ValueError
        if message["method"] != "health":
            code = "unsupported_method"
            raise ValueError
        result = {
            "version": 1,
            "request_id": request_id,
            "result": {
                "service": "betterlinuxcnc",
                "mode": "diagnostics-only",
                "machine_connected": False,
            },
        }
    except (ValueError, UnicodeDecodeError, RecursionError):
        result = {"version": 1, "request_id": request_id, "error": {"code": code}}
    return json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
