"""Minimal, replaceable Flask implementation of the external handoff."""

import base64
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx
from flask import Flask, Response, g, make_response, redirect, render_template, request
from itsdangerous import BadData, URLSafeTimedSerializer

from .config import CALLBACK_PATH, LOGIN_PATH, TOOL_ID, ServiceSettings, load_service_settings

MAX_AGE = 5 * 60
MAX_BODY = 2 * 1024
MAX_USER_RESPONSE = 64 * 1024
CODE = re.compile(r"^[A-Za-z0-9_-]{1,128}$", re.ASCII)
VERIFIER = re.compile(r"^[A-Za-z0-9._~-]{43,128}$", re.ASCII)
USER_ID = re.compile(r"^[0-9a-f]{24}$", re.ASCII)


def pkce_s256_challenge(verifier: str) -> str:
    """Build the only PKCE challenge supported by this example."""
    if not VERIFIER.fullmatch(verifier):
        raise ValueError("Invalid verifier")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _bounded_json(response: httpx.Response, limit: int) -> Any:
    """Decode a small upstream response without trusting its declared size."""
    body = bytearray()
    for chunk in response.iter_bytes():
        body.extend(chunk)
        if len(body) > limit:
            raise ValueError("Response too large")
    return json.loads(body)


def _exchange_result(payload: Any) -> dict[str, Any]:
    required = {"user_id", "display_name", "tool_access_token", "expires_at"}
    if not isinstance(payload, dict) or set(payload) not in (required, required | {"selection"}):
        raise ValueError("Invalid exchange")
    if not isinstance(payload["user_id"], str) or not USER_ID.fullmatch(payload["user_id"]):
        raise ValueError("Invalid exchange")
    if payload["display_name"] is not None and (
        not isinstance(payload["display_name"], str) or len(payload["display_name"]) > 256
    ):
        raise ValueError("Invalid exchange")
    if not isinstance(payload["tool_access_token"], str) or not 0 < len(
        payload["tool_access_token"]
    ) <= 4096:
        raise ValueError("Invalid exchange")
    if not isinstance(payload["expires_at"], str) or len(payload["expires_at"]) > 64:
        raise ValueError("Invalid exchange")
    expiry = datetime.fromisoformat(payload["expires_at"])
    if expiry.tzinfo is None:
        raise ValueError("Invalid exchange")
    selection = payload.get("selection")
    if selection is not None and (
        not isinstance(selection, dict)
        or set(selection) != {"action", "items"}
        or not isinstance(selection["action"], str)
        or not isinstance(selection["items"], list)
        or not 0 < len(selection["action"]) <= 128
        or len(selection["items"]) > 100
        or not all(isinstance(item, str) and 0 < len(item) <= 256 for item in selection["items"])
        or len(selection["items"]) != len(set(selection["items"]))
    ):
        raise ValueError("Invalid exchange")
    return payload


def create_app(
    settings: ServiceSettings | None = None,
    http_client: httpx.Client | None = None,
) -> Flask:
    """Create the one-shot external service; arguments are test seams only."""
    settings = settings or load_service_settings()
    client = http_client or httpx.Client(
        timeout=httpx.Timeout(8, connect=3), follow_redirects=False
    )
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_BODY
    secure = settings.secure_cookies
    prefix = "__Secure-" if secure else ""
    cookie_names = {
        purpose: f"{prefix}datalab_{TOOL_ID.replace('-', '_')}_{purpose}"
        for purpose in ("login_csrf", "callback_csrf", "pkce")
    }

    @app.after_request
    def security_headers(response: Response) -> Response:
        csp = ["default-src 'none'"]
        if nonce := getattr(g, "nonce", None):
            csp.append(f"script-src 'nonce-{nonce}'")
        csp += ["form-action 'self'", "base-uri 'none'", "frame-ancestors 'none'"]
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": "; ".join(csp),
            }
        )
        return response

    def cookie_value(purpose: str, field: str) -> str | None:
        signed = request.cookies.get(cookie_names[purpose])
        try:
            data = URLSafeTimedSerializer(
                settings.cookie_secret, salt=f"{TOOL_ID}:{purpose}:v1"
            ).loads(signed, max_age=MAX_AGE)
        except (BadData, TypeError):
            return None
        if not isinstance(data, dict) or set(data) != {"v", field} or data["v"] != 1:
            return None
        return data[field] if isinstance(data[field], str) else None

    def set_cookie(response: Response, purpose: str, field: str, value: str, path: str) -> None:
        signed = URLSafeTimedSerializer(
            settings.cookie_secret, salt=f"{TOOL_ID}:{purpose}:v1"
        ).dumps({"v": 1, field: value})
        response.set_cookie(
            cookie_names[purpose],
            signed,
            max_age=MAX_AGE,
            secure=secure,
            httponly=True,
            samesite="Lax",
            path=path,
        )

    def clear_cookie(response: Response, purpose: str, path: str) -> None:
        response.delete_cookie(
            cookie_names[purpose],
            secure=secure,
            httponly=True,
            samesite="Lax",
            path=path,
        )

    def exact_form(*names: str) -> dict[str, str] | None:
        length = request.content_length
        if (
            length is None
            or not 0 < length <= MAX_BODY
            or request.mimetype != "application/x-www-form-urlencoded"
            or set(request.form) != set(names)
            or any(len(request.form.getlist(name)) != 1 for name in names)
        ):
            return None
        return {name: request.form[name] for name in names}

    def error() -> Response:
        return make_response(render_template("page.html", page="error"), 400)

    def bridge(field: str, path: str, purpose: str) -> Response:
        csrf = secrets.token_urlsafe(32)
        g.nonce = secrets.token_urlsafe(18)
        response = make_response(
            render_template(
                "page.html",
                page="fragment",
                field_name=field,
                action=path,
                csrf=csrf,
                csp_nonce=g.nonce,
                submission_allowed=not request.query_string,
            )
        )
        set_cookie(response, purpose, "csrf", csrf, path)
        return response

    @app.get("/")
    def index() -> str:
        return render_template("page.html", page="home")

    @app.get("/healthz")
    def healthz() -> Response:
        return Response('{"status":"ok"}\n', mimetype="application/json")

    @app.get(LOGIN_PATH)
    def login_page() -> Response:
        return bridge("datalab_launch_code", LOGIN_PATH, "login_csrf")

    @app.post(LOGIN_PATH)
    def login() -> Response:
        form = exact_form("csrf", "datalab_launch_code")
        expected_csrf = cookie_value("login_csrf", "csrf")
        if (
            form is None
            or not hmac.compare_digest(request.headers.get("Origin", ""), settings.origin)
            or expected_csrf is None
            or not hmac.compare_digest(form["csrf"], expected_csrf)
            or not CODE.fullmatch(form["datalab_launch_code"])
        ):
            return error()
        verifier = secrets.token_urlsafe(32)
        fragment = urlencode(
            {
                "datalab_launch_code": form["datalab_launch_code"],
                "code_challenge": pkce_s256_challenge(verifier),
                "code_challenge_method": "S256",
            }
        )
        response = redirect(f"{settings.authorize_url}#{fragment}", 303)
        clear_cookie(response, "login_csrf", LOGIN_PATH)
        set_cookie(response, "pkce", "verifier", verifier, CALLBACK_PATH)
        return response

    @app.get(CALLBACK_PATH)
    def callback_page() -> Response:
        return bridge("datalab_authorization_code", CALLBACK_PATH, "callback_csrf")

    @app.post(CALLBACK_PATH)
    def callback() -> Response:
        form = exact_form("csrf", "datalab_authorization_code")
        expected_csrf = cookie_value("callback_csrf", "csrf")
        verifier = cookie_value("pkce", "verifier")
        if (
            form is None
            or not hmac.compare_digest(request.headers.get("Origin", ""), settings.origin)
            or expected_csrf is None
            or not hmac.compare_digest(form["csrf"], expected_csrf)
            or verifier is None
            or not VERIFIER.fullmatch(verifier)
            or not CODE.fullmatch(form["datalab_authorization_code"])
        ):
            return error()

        clear_pkce = False
        try:
            exchange_response = client.post(
                settings.exchange_url,
                auth=(TOOL_ID, settings.client_secret),
                json={
                    "authorization_code": form["datalab_authorization_code"],
                    "code_verifier": verifier,
                },
                follow_redirects=False,
            )
            if not 200 <= exchange_response.status_code < 300:
                raise ValueError("Exchange failed")
            clear_pkce = True
            result = _exchange_result(_bounded_json(exchange_response, MAX_BODY))
            user_response = client.get(
                settings.current_user_url,
                headers={"DATALAB-API-KEY": result["tool_access_token"]},
                follow_redirects=False,
            )
            user = _bounded_json(user_response, MAX_USER_RESPONSE)
            if (
                user_response.status_code != 200
                or not isinstance(user, dict)
                or not isinstance(user.get("immutable_id"), str)
                or not hmac.compare_digest(user["immutable_id"], result["user_id"])
            ):
                raise ValueError("Subject mismatch")
            response = make_response(
                render_template(
                    "page.html",
                    page="result",
                    display_name=result["display_name"] or "Datalab user",
                    selection=result.get("selection"),
                )
            )
        except (httpx.HTTPError, ValueError, TypeError):
            response = error()
        clear_cookie(response, "callback_csrf", CALLBACK_PATH)
        if clear_pkce:
            clear_cookie(response, "pkce", CALLBACK_PATH)
        return response

    return app
