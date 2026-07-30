from datalab_hello_standalone_tool import __version__
from datalab_hello_standalone_tool.provider import (
    HelloStandaloneToolProvider,
)


def test_provider_metadata():
    provider = HelloStandaloneToolProvider()

    assert provider.id == "hello-standalone"
    assert provider.metadata.version == __version__
    assert provider.metadata.ui.kind == "standalone"
