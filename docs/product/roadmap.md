# PM Studio — Product Roadmap

> "The PM Studio Roadmap is organized by platform capabilities. Each capability represents a reusable functional evolution for Product Managers."

---

# Vision

Build an open source AI Product Engineering platform capable of supporting Product Managers throughout the entire product development cycle.

PM Studio evolution happens through incremental capabilities, reusing a common architecture and maintaining low coupling between its components.

---

# Capabilities

| Capability | Status | Sprint |
|------------|--------|---------|
| Foundation | ✅ Completed | Sprint 001 |
| Core Architecture | ✅ Completed | Sprint 002 |
| Create PRD | ✅ Completed | Sprint 003 |
| Web Interface | ✅ Completed | Sprint 004 |
| Configuration Layer | ✅ Completed | Sprint 004 |
| Multi Provider AI | ✅ Completed | Sprint 004 |
| MCP Server (Context) | ✅ Completed | Sprint 004 |
| Integration Tests | ✅ Completed | Sprint 004 |
| Auth & Login | ✅ Completed | Sprint 004 |
| Product Docs Hub | ✅ Completed | Sprint 004 |
| Timeline / Roadmap | ✅ Completed | Sprint 004 |
| PRD Version History | ✅ Completed | Sprint 004 |
| Validation with Diff | ✅ Completed | Sprint 004 |
| Secure Authentication Foundation | ✅ Completed | Sprint 007 |
| Demo Mode (No External AI) | ✅ Completed | Sprint 007 |
| Reproducible Setup & CI | ✅ Completed | Sprint 007 |
| Open Source Governance | ✅ Completed | Sprint 007 |
| Functional MCP Server | ✅ Completed | Sprint 007 |
| Create Backlog | 🟡 Planned | Sprint 005 |
| OKRs | 🟡 Planned | Sprint 005 |
| AI Prototyping | 🟡 Planned | Sprint 006 |
| Security Score | 🟡 Planned | Sprint 006 |
| Metrics Integration | 🔵 Backlog | Sprint 007 |
| Competitive Analysis | 🔵 Backlog | Sprint 007 |
| Auto Release Notes | 🔵 Backlog | Sprint 008 |
| Experiment Plans | 🔵 Backlog | Sprint 008 |
| Vector Store | ⚪ Future | TBD |
| Knowledge Graph | ⚪ Future | TBD |

---

# Current Focus

## Sprint 007 — Trust and Access

### Delivered

- Argon2 passwords with automatic migration of legacy hashes.
- Expiring, one-time password reset links.
- CSRF coverage for state-changing routes.
- Demo mode with no external model call.
- Reproducible dependencies, test matrix and linting in CI.
- Functional MCP tools and open source governance files.

### Next

- Structured context with source metadata and citations.
- Privacy preview before sending context to a provider.
- Persistent jobs scoped to user and squad.
- Learning path for Product Managers beginning with AI.

---

# Long-Term Vision

PM Studio should evolve into a platform composed of several reusable capabilities.

Each new capability should reuse existing Core components, preserving the architecture built in the first Sprints.

The project evolution will follow the principles of:

- Context Engineering;
- AI as a Dependency;
- Domain-Driven Design;
- Capability-oriented architecture;
- Incremental evolution.

---

# Criteria for New Capabilities

A new capability will only be added when it:

- reuses the existing architecture;
- represents a complete use case;
- provides value for Product Managers;
- does not increase platform coupling;
- respects PM Studio architectural principles.
