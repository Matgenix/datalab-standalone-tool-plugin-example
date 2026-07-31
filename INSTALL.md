# Installation and development

Install [uv](https://docs.astral.sh/uv/) and clone the repository:

```shell
git clone https://github.com/Matgenix/datalab-standalone-tool-plugin-example.git
cd datalab-standalone-tool-plugin-example
uv sync --locked --all-extras --dev
uv run pre-commit install
```



## Install in a datalab checkout

Add the plugin to the datalab checkout's root `plugins.toml`:

```toml
dependencies = ["datalab-hello-standalone-tool"]

[tool.uv.sources]
datalab-hello-standalone-tool = { git = "https://github.com/Matgenix/datalab-standalone-tool-plugin-example.git" }
```

Preserve existing dependencies and source entries when merging this
configuration. Pin a release tag or commit for reproducible deployments. Then
install the configured plugins:

```shell
cd pydatalab
uv run invoke dev.install
```

Restart the datalab API after installation so it discovers the
`pydatalab.tools` entry point.
