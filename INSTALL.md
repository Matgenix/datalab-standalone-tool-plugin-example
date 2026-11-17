# Installation

This plugin runs trusted Python in the datalab API. Review the selected release
and its dependencies before installation or upgrade. Production standalone
launches require HTTPS; plain HTTP is accepted only for explicit loopback hosts
during local development.

## Install in datalab

Add the plugin to the datalab checkout's root `plugins.toml`, preserving any
existing entries:

```toml
dependencies = ["datalab-hello-standalone-tool"]

[tool.uv.sources]
datalab-hello-standalone-tool = { git = "https://github.com/Matgenix/datalab-standalone-tool-plugin-example.git", rev = "<reviewed-tag-or-commit>" }
```

Install the configured plugins:

```shell
cd pydatalab
uv run invoke dev.install
```

Restart a native API, or rebuild and recreate the Docker images. Sign in as a
normal user, launch **Hello standalone** from **Tools**, and test **Open
selected** with an accessible item.

Use datalab's
[plugin operations guide](https://docs.datalab-org.io/en/latest/plugins/#installing-and-maintaining-plugins)
for Docker behavior, upgrades, rollback, removal, and tool ordering or disabling.

## Development setup

```shell
git clone https://github.com/Matgenix/datalab-standalone-tool-plugin-example.git
cd datalab-standalone-tool-plugin-example
uv sync --locked --all-extras --dev
uv run pytest
uv run pre-commit run --all-files
```

For integration testing, change the Git source above to an editable path to
this checkout, rerun `uv run invoke dev.install`, and restart datalab.
