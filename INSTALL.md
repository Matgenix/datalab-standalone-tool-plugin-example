# Installation

This plugin runs trusted code in the datalab API process. Review the
selected release, dependencies, and built assets before installing it.

## Install in datalab

Add the plugin to the datalab checkout's root `plugins.toml`, preserving any
existing dependencies and source entries:

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

Restart a native datalab API, or rebuild and recreate its Docker images. Sign in
as a normal user and confirm that **Hello standalone** appears under **Tools**
and that **Open selected** appears for a valid selection in the
configured item tables.

The generic datalab
[plugin operations guide](https://docs.datalab-org.io/en/latest/plugins/#installing-and-maintaining-plugins)
is the source for Docker behavior, upgrades, rollback, removal, and tool ordering
or disabling.


## Run the independent external service

Installing the provider does not start the external app. Configure the five
variables listed in `.env.example`, generating two distinct high-entropy
secrets.

Run the replaceable reference service natively:

```shell
uv sync --locked --extra service
uv run gunicorn --bind 127.0.0.1:8000 'datalab_hello_standalone_tool.service:create_app()'
```

Or build the independent image:

```shell
docker build -t datalab-standalone-tool-plugin-example:<reviewed-version> .
docker run --rm --env-file /path/to/tool.env -p 127.0.0.1:8000:8000 datalab-standalone-tool-plugin-example:<reviewed-version>
```

> **TODO:** Replace these development commands with production deployment,
> proxy, TLS, secret-management, logging, health-check, upgrade, and rollback
> instructions for the real application.


## Development setup

Install [uv](https://docs.astral.sh/uv/), then clone and check the project:

```shell
git clone https://github.com/Matgenix/datalab-standalone-tool-plugin-example.git
cd datalab-standalone-tool-plugin-example
uv sync --locked --all-extras --dev
uv run pytest
uv run pre-commit run --all-files
```


For local service testing, export loopback URLs and distinct secrets, then run
`uv run flask --app 'datalab_hello_standalone_tool.service:create_app()' run --port 8000`.
The provider adapter still runs in the separately started Datalab API.




For integration testing, replace the Git source above with an editable path to
this checkout. Rerun `uv run invoke dev.install`, restart datalab, and exercise
the tool as a normal user.
