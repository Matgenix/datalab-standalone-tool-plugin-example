# Hello standalone

Hello standalone is a minimal example that opens outside datalab and makes one
permission-filtered API request with temporary access.

## Use the tool

To open it without a selection, sign in to datalab, click **Tools**, and choose
**Hello standalone**. The new page reports how many samples you can access.

To pass items to it:

1. Select 1–20 rows in Samples, Inventory, or the items in a collection.
2. Choose **Open selected** from the selected-items menu.
3. Confirm that the standalone page lists the ordered refcodes received from
   datalab.

The access token is temporary and one relaunch replaces the previous session.
That behavior is a deliberate use of datalab's default replacement policy, not
a requirement for every standalone application. Trusted provider code can
select `REUSE_OR_REPLACE` or `INDEPENDENT`; a service that retains a candidate
and offers explicit renewal must also provide an appropriate trusted
confirmation boundary. The
[standalone session contract](https://docs.datalab-org.io/en/latest/plugin-development/standalone-tool-plugin/#access-and-credential-details)
documents those advanced options.

If the page reports an expired session or HTTP 401, close it and launch the tool
again from datalab. Do not copy or share the launch URL.

Deployment administrators should follow the repository's
[installation guide](https://github.com/Matgenix/datalab-standalone-tool-plugin-example/blob/main/INSTALL.md).
Developers can reproduce the launch exchange with datalab's
[standalone tool tutorial](https://docs.datalab-org.io/en/latest/plugin-development/standalone-tool-plugin/).
