"""Validated configuration shared by the provider adapter and external service."""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

TOOL_ID = "hello-standalone"
ENV_PREFIX = "DATALAB_HELLO_STANDALONE"
LOGIN_PATH = "/datalab-login"
CALLBACK_PATH = "/datalab-callback"
EXCHANGE_PATH = f"/v0.1/tools/plugins/{TOOL_ID}/exchange"
AUTHORIZE_PATH = f"/v0.1/tools/{TOOL_ID}/service-launch/authorize"
CURRENT_USER_PATH = "/v0.1/get-current-user/"
MINIMUM_SECRET_LENGTH = 32


class ConfigurationError(ValueError):
    """Raised when deployment configuration is absent or unsafe."""


def _is_loopback(hostname: str | None) -> bool:
    if hostname is None:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _validated_url(value: str, name: str, *, origin_only: bool) -> str:
    if not value or value != value.strip() or "\\" in value:
        raise ConfigurationError(f"{name} must be a canonical absolute URL")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ConfigurationError(f"{name} has an invalid port") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.startswith("//")
        or "/./" in parsed.path
        or "/../" in parsed.path
        or parsed.path.endswith("/.")
        or parsed.path.endswith("/..")
    ):
        raise ConfigurationError(f"{name} must be an absolute HTTP(S) URL without decorations")
    if parsed.scheme == "http" and not _is_loopback(parsed.hostname):
        raise ConfigurationError(f"{name} must use HTTPS outside explicit loopback development")
    if origin_only and parsed.path not in {"", "/"}:
        raise ConfigurationError(f"{name} must contain only an origin")
    path = "" if origin_only else parsed.path.rstrip("/")
    hostname = parsed.hostname.lower()
    if ":" in hostname:
        hostname = f"[{hostname}]"
    netloc = hostname if port is None else f"{hostname}:{port}"
    return urlunsplit((parsed.scheme.lower(), netloc, path, "", ""))


def _required_secret(environment: Mapping[str, str], suffix: str) -> str:
    name = f"{ENV_PREFIX}_{suffix}"
    value = environment.get(name, "")
    if len(value) < MINIMUM_SECRET_LENGTH or value != value.strip():
        raise ConfigurationError(f"{name} must contain at least {MINIMUM_SECRET_LENGTH} characters")
    return value


def join_url(base_url: str, fixed_path: str) -> str:
    """Append one trusted absolute path to a validated API base URL."""
    if not fixed_path.startswith("/") or fixed_path.startswith("//"):
        raise ValueError("The fixed URL path must be absolute and unambiguous")
    parsed = urlsplit(base_url)
    base_path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, f"{base_path}{fixed_path}", "", ""))


@dataclass(frozen=True)
class ProviderSettings:
    """Startup-validated settings used inside the Datalab API process."""

    public_url: str
    client_secret: str = field(repr=False)

    @property
    def login_url(self) -> str:
        return f"{self.public_url}{LOGIN_PATH}"

    @property
    def callback_url(self) -> str:
        return f"{self.public_url}{CALLBACK_PATH}"


@dataclass(frozen=True)
class ServiceSettings:
    """Startup-validated settings used by the external web process."""

    public_url: str
    datalab_browser_api_url: str
    datalab_api_url: str
    client_secret: str = field(repr=False)
    cookie_secret: str = field(repr=False)

    @property
    def secure_cookies(self) -> bool:
        return urlsplit(self.public_url).scheme == "https"

    @property
    def origin(self) -> str:
        return self.public_url

    @property
    def authorize_url(self) -> str:
        return join_url(self.datalab_browser_api_url, AUTHORIZE_PATH)

    @property
    def exchange_url(self) -> str:
        return join_url(self.datalab_api_url, EXCHANGE_PATH)

    @property
    def current_user_url(self) -> str:
        return join_url(self.datalab_api_url, CURRENT_USER_PATH)


def load_provider_settings(environment: Mapping[str, str] | None = None) -> ProviderSettings:
    """Load and validate the provider adapter's environment once at startup."""
    values = os.environ if environment is None else environment
    public_name = f"{ENV_PREFIX}_PUBLIC_URL"
    return ProviderSettings(
        public_url=_validated_url(values.get(public_name, ""), public_name, origin_only=True),
        client_secret=_required_secret(values, "CLIENT_SECRET"),
    )


def load_service_settings(environment: Mapping[str, str] | None = None) -> ServiceSettings:
    """Load and validate all external-service settings."""
    values = os.environ if environment is None else environment
    public_name = f"{ENV_PREFIX}_PUBLIC_URL"
    browser_name = f"{ENV_PREFIX}_DATALAB_BROWSER_API_URL"
    api_name = f"{ENV_PREFIX}_DATALAB_API_URL"
    client_secret = _required_secret(values, "CLIENT_SECRET")
    cookie_secret = _required_secret(values, "COOKIE_SECRET")
    if client_secret == cookie_secret:
        raise ConfigurationError("The client and cookie secrets must be different")
    return ServiceSettings(
        public_url=_validated_url(values.get(public_name, ""), public_name, origin_only=True),
        datalab_browser_api_url=_validated_url(
            values.get(browser_name, ""), browser_name, origin_only=False
        ),
        datalab_api_url=_validated_url(values.get(api_name, ""), api_name, origin_only=False),
        client_secret=client_secret,
        cookie_secret=cookie_secret,
    )
