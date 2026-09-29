"""Single-user access sessions, CSRF defense and bounded request bodies."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from starlette.responses import JSONResponse

COOKIE = "reference_lab_session"


def signature(token: str, message: str) -> str:
    return hmac.new(token.encode(), message.encode(), hashlib.sha256).hexdigest()


def make_session(token: str) -> str:
    payload = f"{int(time.time())}.{secrets.token_hex(16)}"
    return payload + "." + signature(token, payload)


def valid_session(token: str, session: str) -> bool:
    try:
        timestamp, nonce, proof = session.split(".")
        age = time.time() - int(timestamp)
        return 0 <= age < 86400 and len(nonce) == 32 and hmac.compare_digest(proof, signature(token, timestamp + "." + nonce))
    except (ValueError, TypeError):
        return False


def csrf_for(token: str, session: str) -> str:
    return signature(token, "csrf:" + session)


class BodyLimitMiddleware:
    """Bound the entire body before parsers/middleware can swallow a limit exception.

    Memory is capped per request by `limit`; deployments must also enforce proxy
    concurrency/rate limits. No unbounded buffering or request-body logging.
    """
    def __init__(self, app, limit: int):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await JSONResponse({"message": "Invalid content length"}, 400)(scope, receive, send)
        if length < 0 or length > self.limit:
            return await JSONResponse({"message": "Request body is too large"}, 413)(scope, receive, send)
        chunks, size = [], 0
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            if event["type"] != "http.request":
                continue
            size += len(event.get("body", b""))
            if size > self.limit:
                return await JSONResponse({"message": "Request body is too large"}, 413)(scope, receive, send)
            chunks.append(event)
            if not event.get("more_body", False):
                break
        iterator = iter(chunks)
        async def replay():
            try:
                return next(iterator)
            except StopIteration:
                return await receive()
        await self.app(scope, replay, send)
