from datalab_hello_standalone_tool.config import ServiceSettings
from datalab_hello_standalone_tool.service import create_app


def test_service_starts():
    """Replace this smoke test with tests for the real application."""
    settings = ServiceSettings(
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5001",
        "http://127.0.0.1:5001",
        "c" * 32,
        "k" * 32,
    )

    response = create_app(settings).test_client().get("/healthz")

    assert response.json == {"status": "ok"}
