# datalab Hello Standalone Tool

Minimal *standalone tool* plugin. It opens in a new tab, exchanges a *launch code*,
and prints one datalab-backed message. datalab automatically protects its
*provider blueprint* with the active *browser session*; the resulting *tool access
token* accesses *samples* through the normal *permission-aware API*.

## Local installation

Add the package to the root `plugins.toml`:

```toml
dependencies = ["datalab-hello-standalone-tool"]

[tool.uv.sources]
datalab-hello-standalone-tool = { path = "dev-repos/datalab-standalone-tool-plugin-example", editable = true }
```

Then install datalab with plugins:

```shell
cd pydatalab
uv run invoke dev.install
```

See the
[standalone Tool plugin tutorial](https://docs.datalab-org.io/plugin-development/standalone-tool-plugin/)
for a step-by-step explanation.
