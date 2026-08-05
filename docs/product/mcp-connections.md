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

## Initiative assistant

The initiative assistant lists discovered tools from enabled Streamable HTTP
connections marked as `read_only`. For each message, the user explicitly
selects one tool and provides an arguments object in JSON. PM Studio validates
the connection and tool again on the server, executes one `tools/call`, limits
the returned content, and labels it as untrusted external data before adding it
to the AI context. The conversation history records the connection and tool
that were used.

Connections marked `confirm_writes`, disabled connections, stdio processes and
tools absent from the stored discovery result cannot be called by the
assistant. A confirmation journey for write tools remains future work.

## Current boundaries

- MCP capability discovery is available for HTTP and stdio.
- Existing legacy HTTP context sources remain compatible.
- Generic discovered tools are not automatically injected into PRD generation.
- OAuth browser flows and governed write-tool execution require separate
  product journeys.
