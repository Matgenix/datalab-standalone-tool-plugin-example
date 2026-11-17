from dataclasses import dataclass
from types import SimpleNamespace

from flask import Flask

from datalab_hello_standalone_tool import __version__
from datalab_hello_standalone_tool import provider as provider_module
from datalab_hello_standalone_tool.provider import (
    TOOL_BLUEPRINT,
    HelloStandaloneToolProvider,
)


@dataclass
class FakeGrants:
    client_id: str | None = None

    def issue(self, client_id):
        self.client_id = client_id
        return "single-use-code"


def test_provider_metadata():
    provider = HelloStandaloneToolProvider()

    assert provider.id == "hello-standalone"
    assert provider.metadata.version == __version__
    assert provider.metadata.ui.kind == "standalone"
    assert provider.metadata.icon == "laptop-code"
    action = provider.metadata.launch_actions[0]
    assert action.id == "open-selected"
    assert action.tables == ("samples", "inventory", "collection-items")


def test_launch_returns_fragment_url_and_binds_client():
    provider = HelloStandaloneToolProvider()
    grants = FakeGrants()
    app = Flask(__name__)

    with app.test_request_context("/v0.1/tools/hello-standalone/launch"):
        url = provider.launch(SimpleNamespace(), grants)

    assert grants.client_id == "hello-standalone"
    assert url == (
        "http://localhost/v0.1/tools/plugins/hello-standalone/"
        "index.html#datalab_launch_code=single-use-code"
    )


def test_exchange_rejects_missing_code_and_returns_no_store(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(TOOL_BLUEPRINT, url_prefix="/tool")
    monkeypatch.setattr(
        provider_module,
        "current_user",
        SimpleNamespace(person=SimpleNamespace(immutable_id="user-id")),
    )
    exchange = SimpleNamespace(
        tool_session=SimpleNamespace(tool_access_token="temporary-token"),  # noqa: S106
        selection=SimpleNamespace(
            action_id="open-selected",
            item_refcodes=("demo:one", "demo:two"),
        ),
    )

    def exchange_for_current_user(code, tool_id, client_id, *, expected_user_id):
        assert (code, tool_id, client_id) == (
            "launch-code",
            "hello-standalone",
            "hello-standalone",
        )
        assert expected_user_id == "user-id"
        return exchange

    monkeypatch.setattr(provider_module, "exchange_launch_code", exchange_for_current_user)

    client = app.test_client()
    assert client.post("/tool/exchange", json={}).status_code == 400

    response = client.post("/tool/exchange", json={"code": "launch-code"})
    assert response.status_code == 200
    assert response.json == {
        "tool_access_token": "temporary-token",
        "selection": {
            "action": "open-selected",
            "items": ["demo:one", "demo:two"],
        },
    }
    assert response.headers["Cache-Control"] == "no-store"


def test_exchange_rejects_invalid_or_expired_code(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(TOOL_BLUEPRINT, url_prefix="/tool")
    monkeypatch.setattr(
        provider_module,
        "current_user",
        SimpleNamespace(person=SimpleNamespace(immutable_id="user-id")),
    )
    monkeypatch.setattr(provider_module, "exchange_launch_code", lambda *args, **kwargs: None)

    response = app.test_client().post("/tool/exchange", json={"code": "expired-code"})

    assert response.status_code == 400
    assert response.json == {"error": "Invalid or expired launch code"}


def test_standalone_page_uses_delegated_token_without_browser_credentials():
    app = Flask(__name__)
    app.register_blueprint(TOOL_BLUEPRINT, url_prefix="/tool")
    response = app.test_client().get("/tool/index.html")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'headers: { "DATALAB-API-KEY": exchange.tool_access_token }' in page
    assert 'credentials: "omit"' in page
    assert "exchange.selection?.items?.length" in page
