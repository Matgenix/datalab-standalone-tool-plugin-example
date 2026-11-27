"""Datalab-side provider adapter for the external Hello standalone service."""

import hmac
import json
import re
from datetime import timezone
from functools import lru_cache
from urllib.parse import urlencode

from flask import Blueprint, jsonify, request
from pydatalab.tools import (
    ItemTableSelectionAction,
    StandaloneToolUI,
    ToolContext,
    ToolLaunchGrantIssuer,
    ToolMetadata,
    ToolProvider,
    ToolRouteAuth,
    exchange_authorized_service_launch_code,
)

from ._version import __version__
from .config import ProviderSettings, load_provider_settings

TOOL_ID = "hello-standalone"
TOOL_BLUEPRINT = Blueprint("datalab_hello_standalone_tool", __name__)
MAX_REQUEST_BYTES = 2 * 1024
TOOL_SESSION_LIFETIME_SECONDS = 5 * 60
_HANDOFF_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$", re.ASCII)
_VERIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{43,128}$", re.ASCII)
_INVALID_EXCHANGE: dict[str, object] = {"error": "Invalid or expired authorization"}


@lru_cache(maxsize=1)
def _settings() -> ProviderSettings:
    return load_provider_settings()


def _response(payload: dict[str, object], status: int):
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response, status


def _invalid_exchange(status: int = 400):
    return _response(_INVALID_EXCHANGE, status)


def _exact_exchange_payload() -> tuple[str, str] | None:
    length = request.content_length
    if (
        length is None
        or not 0 < length <= MAX_REQUEST_BYTES
        or request.content_type != "application/json"
    ):
        return None
    raw = request.get_data(cache=False, as_text=False)
    if len(raw) != length or len(raw) > MAX_REQUEST_BYTES:
        return None
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(payload, dict) or set(payload) != {"authorization_code", "code_verifier"}:
        return None
    authorization_code = payload["authorization_code"]
    code_verifier = payload["code_verifier"]
    if (
        not isinstance(authorization_code, str)
        or not _HANDOFF_CODE_PATTERN.fullmatch(authorization_code)
        or not isinstance(code_verifier, str)
        or not _VERIFIER_PATTERN.fullmatch(code_verifier)
    ):
        return None
    return authorization_code, code_verifier


@TOOL_BLUEPRINT.post("/exchange")
def exchange():
    """Exchange one browser-authorized PKCE code for a short delegated token."""
    payload = _exact_exchange_payload()
    if payload is None:
        return _invalid_exchange()
    authorization_code, code_verifier = payload
    result = exchange_authorized_service_launch_code(
        authorization_code,
        code_verifier,
        TOOL_ID,
        TOOL_ID,
        tool_session_lifetime_seconds=TOOL_SESSION_LIFETIME_SECONDS,
    )
    if result is None:
        return _invalid_exchange()

    expires_at = result.tool_session.expires_at
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    response_data: dict[str, object] = {
        "user_id": result.context.user_id,
        "display_name": result.context.display_name,
        "tool_access_token": result.tool_session.tool_access_token,
        "expires_at": expires_at.isoformat(),
    }
    if result.selection is not None:
        response_data["selection"] = {
            "action": result.selection.action_id,
            "items": list(result.selection.item_refcodes),
        }
    return _response(response_data, 200)


class HelloStandaloneToolProvider(ToolProvider):
    """Provide Hello standalone through datalab's Tools catalog."""

    id = TOOL_ID
    metadata = ToolMetadata(
        name="Hello standalone",
        description="A standalone Hello World tool for datalab",
        version=__version__,
        icon="laptop-code",
        ui=StandaloneToolUI(),
        launch_actions=(
            ItemTableSelectionAction(
                id="open-selected",
                label="Open selected",
                tables=(
                    "samples",
                    "inventory",
                    "collection-items",
                ),
                min_items=1,
                max_items=20,
            ),
        ),
    )
    blueprint = TOOL_BLUEPRINT
    route_auth = ToolRouteAuth.SERVICE

    def __init__(self, settings: ProviderSettings | None = None):
        self._provider_settings = _settings() if settings is None else settings

    def authenticate_service_request(self) -> bool:
        """Authenticate the fixed confidential client with constant-time comparisons."""
        authorization = request.authorization
        username = authorization.username if authorization and authorization.type == "basic" else ""
        password = authorization.password if authorization and authorization.type == "basic" else ""
        return hmac.compare_digest(username or "", TOOL_ID) & hmac.compare_digest(
            password or "", self._provider_settings.client_secret
        )

    def launch(
        self,
        context: ToolContext,
        grants: ToolLaunchGrantIssuer,
    ) -> str:
        """Issue a pending service launch and return the fixed external login URL."""
        del context
        code = grants.issue_service_launch(
            TOOL_ID,
            self._provider_settings.callback_url,
            lifetime_seconds=5 * 60,
        )
        fragment = urlencode({"datalab_launch_code": code})
        return f"{self._provider_settings.login_url}#{fragment}"
