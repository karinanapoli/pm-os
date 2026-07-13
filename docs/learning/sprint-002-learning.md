# Sprint 002 Learning Journal

## What we learned

During this Sprint we consolidated several fundamental architecture concepts.

### Workflows

We learned that Workflows represent use cases.

They orchestrate components.

They don't implement specific business rules.

---

### Dependency Injection

We learned to receive dependencies through the constructor.

This reduces coupling.

---

### Protocols

We created contracts using typing.Protocol.

The Core now depends on behavior, not implementations.

---

### Composition Root

We introduced Bootstrap.

All application assembly now happens in a single place.

---

### Tests

We created the first unit tests of the project.

Tested components:

- AIClient
- PromptBuilder
- MarkdownWriter

---

### Product

The biggest discovery of the Sprint was realizing that PM OS is not a PRD generator.

It is an Operating System for product initiatives.

The real asset of the system is the context.
