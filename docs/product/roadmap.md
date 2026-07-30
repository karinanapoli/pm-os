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
| Traceable Context Sources | ✅ Completed | Sprint 008 |
| Privacy Preview | ✅ Completed | Sprint 008 |
| Evidence-aware Prompts | ✅ Completed | Sprint 008 |
| Persistent Scoped Jobs | ✅ Completed | Sprint 009 |
| Source-level Context Controls | ✅ Completed | Sprint 009 |
| Citation Verification | ✅ Completed | Sprint 009 |
| Architecture & Performance Hardening | ✅ Completed | Sprint 009 |
| Guided Product Specification (Beta) | ✅ Completed | Sprint 010 |
| Decisions, Approval & Consistency Analysis | ✅ Completed | Sprint 010 |
| Traceable Backlog from Approved Specification | 🧪 Beta | Sprint 010 |
| Generic MCP Connections (HTTP and stdio) | ✅ Completed | Sprint 011 |
| Product Signal Memory | ✅ Completed | Sprint 011 |
| Reviewable Signal Extraction from Sources | ✅ Completed | Sprint 011 |
| Cross-Initiative Decision Memory | ✅ Completed | Sprint 012 |
| Decision Review Conditions and Lifecycle | ✅ Completed | Sprint 012 |
| Initiative Traceability Map | ✅ Completed | Sprint 013 |
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

## Sprint 013 — Initiative Map

### Delivered

- Single view connecting signals, initiative sources, specification, decisions,
  and derived deliverables.
- Direct navigation to the owning context and editing journeys.
- Clear ready or pending state for specification, PRD, backlog, and validation.
- Responsive three-stage flow: context → definition → deliverables.
- In-product roadmap synchronized with Signals, Decision Memory, generic MCP,
  traceable backlog, and Initiative Map availability.

### Compatibility

- The map is a derived read-only view.
- Existing artifacts and workspace files remain the sources of truth.
- No initiative migration is required.

## Previous focus — Sprint 012

### Delivered

- Workspace-wide view of decisions recorded in initiative specifications.
- Explicit `revisit if` condition for observable review triggers.
- Active, revisited, and superseded lifecycle states.
- Status filters and direct navigation back to the owning initiative.
- Backward-compatible defaults for existing decisions.

### Safety and ownership

- The initiative specification remains the source of truth.
- The global memory is a derived view and does not duplicate decision files.
- Status changes are explicit user actions.
- Personal and squad scope follow the existing initiative repository rules.

## Previous focus — Sprint 011

### Delivered

- Signals scoped to personal workspaces and squads.
- Relationships between signals and initiatives.
- PDF, Markdown and TXT sources with protected download.
- Local suggestion preparation by default.
- Optional AI-assisted extraction with explicit provider disclosure.
- Human review before any suggested signal is saved.
- Generic MCP registration through HTTP or stdio.
- Safe stdio process execution without a shell and with bounded timeouts.
- Encrypted MCP credentials and environment values.

### Compatibility and safety

- Existing initiatives, specifications and PRDs require no migration.
- A document is a source; it is never accepted as a signal automatically.
- AI extraction falls back to local preparation when the provider fails.
- Sources cannot cross personal and squad scopes.
- MCP write tools are never executed automatically.

## Previous focus — Sprint 010

### Delivered

- Optional guided experience without removing quick PRD generation.
- Versioned product specification with evidence, hypotheses and open questions.
- Non-blocking clarification and consistency findings.
- Explicit decisions and human approval.
- PRD compatibility and automatic quick-flow specification bootstrap.
- Initial traceable backlog generation from an approved specification (Beta).
- Derived-artifact freshness status and portable Markdown downloads.

### Compatibility

- Quick mode remains the default.
- Existing initiatives and PRDs require no migration.
- External systems are never changed automatically.

## Previous foundation

- Argon2 passwords with automatic migration of legacy hashes.
- Expiring, one-time password reset links.
- CSRF coverage for state-changing routes.
- Demo mode with no external model call.
- Reproducible dependencies, test matrix and linting in CI.
- Functional MCP tools and open source governance files.

- Structured context with stable source IDs and metadata.
- Evidence citations and separation of facts, inferences, and recommendations.
- Privacy, confidentiality, and size preview before generation.
- Learning module for Product Managers beginning with context engineering.
- Persistent generation jobs scoped to user and squad, with retention.
- Source-level controls and citation verification.
- Transactional configuration updates and protected public integrations.
- Focused services for PRD generation, validation, consultation, initiatives,
  Product Docs and MCP context collection.
- Bounded parallel MCP fetching.
- CI coverage floor raised to 80%.

### Next

- Complete backlog creation, review, editing, prioritization, and export journey.
- Preview and governed export of backlog items to external systems.
- Structured latency and reliability telemetry.
- Route-module extraction as the web composition root evolves.

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
