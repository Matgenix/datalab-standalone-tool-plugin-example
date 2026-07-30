# Hello standalone

A minimal standalone Hello World tool for datalab

This package provides a trusted datalab
standalone tool
through the `pydatalab.tools` entry-point group.

It demonstrates a single-use launch-code exchange and one permission-filtered
API request using an in-memory temporary tool access token.

See the
[installation guide](https://github.com/Matgenix/datalab-standalone-tool-plugin-example/blob/main/INSTALL.md)
and the
[standalone tool plugin tutorial](https://docs.datalab-org.io/plugin-development/standalone-tool-plugin/).

## Trust

Tool plugins execute trusted Python code in the datalab API process.

Deployment administrators must review source code, dependencies, compiled
assets, maintainers, and release provenance before installation or upgrade.
