# ADR-001 — PM OS will have a Core independent from the MCP

**Status:** Accepted

**Date:** Sprint 001

---

# Context

At the beginning of the project, the idea was to build an MCP server capable of executing workflows for Product Managers.

During Sprint 001 we realized that concentrating all logic inside the MCP would make the architecture strongly coupled to the protocol.

This would make it difficult to:

- test;
- reuse;
- evolve the project;
- integrate with other interfaces.

We needed to decide where the main logic should live.

---

# Options Considered

## Option A

All logic inside the MCP.

Flow:

Continue

↓

MCP

↓

Code

### Advantages

- faster initial implementation.

### Disadvantages

- high coupling;
- difficult reuse;
- hard to test;
- impossible to create CLI without duplicating code.

---

## Option B

Create an independent Core.

Flow:

Interface

↓

MCP

↓

PM OS Core

↓

Workflows

↓

Domain

### Advantages

- modular architecture;
- reusability;
- independent testing;
- possibility to create CLI;
- possibility to create web interface;
- possibility to switch Continue for another interface.

### Disadvantages

- requires an extra layer.

---

# Decision

We chose Option B.

All PM OS knowledge will reside inside the PM OS Core.

The MCP will be only a layer responsible for exposing tools.

The Core will not know about MCP.

---

# Consequences

This decision allows, in the future, the same Core to be used by:

- MCP
- CLI
- API
- Web Interface
- Continue
- OpenCode
- Claude Desktop
- Cursor

Without changes to the business logic.

---

# Principle Created

**The Core will never depend on the interface.**

Interfaces will depend on the Core.

This principle now guides all PM OS architecture.
