# MCP Connections

## Supported transports

PM Studio provides a generic registration experience under
**Settings → External sources**:

- **HTTP** connects to a remote MCP server through Streamable HTTP;
- **stdio** starts a trusted MCP server as a local process.

BusinessMap is an example configuration, not a privileged integration.

## HTTP

An HTTP connection contains a name, server URL, authentication configuration,
and usage policy. Bearer tokens and API keys are supported. Use HTTPS for
remote production servers.

## stdio

A stdio connection contains:

- executable command;
- one argument per line;
- optional environment values in `NAME=value` format;
- usage policy.

The process is started directly without a shell, receives a bounded timeout,
and is terminated after capability discovery. Only configure commands you
trust. Environment values are encrypted at rest and are never rendered back
into the settings page.

## Capability discovery and authorization

Testing a connection performs the MCP initialization handshake and lists
available tools. Registration and discovery do not authorize automatic writes.
PM Studio records read-only or confirm-before-write intent, and it does not
execute writing tools automatically.

## Current boundaries

- MCP capability discovery is available for HTTP and stdio.
- Existing legacy HTTP context sources remain compatible.
- Generic discovered tools are not automatically injected into PRD generation.
- OAuth browser flows and governed tool execution require separate product
  journeys.
