# ADR-002 — PM OS will use Context Engineering instead of Document Loading

**Status:** Accepted

**Date:** Sprint 001

---

# Context

During the initial implementation of PM OS, the need arose to read all documents from a Feature to send them to the AI model.

The first idea was to create a component called `DocumentLoader`.

However, we realized this responsibility would be much larger than just loading files.

We needed to decide what the true responsibility of this component would be.

---

# Problem

A Large Language Model does not understand files.

It understands context.

Sending documents directly to the model creates several problems:

- duplicate documents;
- irrelevant information;
- disorganized context;
- token waste;
- low response quality.

It was necessary to create a layer responsible for preparing this context.

---

# Options Considered

## Option A

Create a DocumentLoader.

Responsibility:

- open files;
- return text.

### Advantages

- simple implementation.

### Disadvantages

- little business responsibility;
- does not allow future evolution;
- mixes infrastructure with context preparation.

---

## Option B

Create a ContextBuilder.

Responsibility:

- read documents;
- organize information;
- remove redundancies;
- add complementary knowledge;
- apply templates;
- structure context for AI.

### Advantages

- represents a domain responsibility;
- separates infrastructure from AI preparation;
- facilitates reuse;
- allows project growth.

### Disadvantages

- initially more abstract component.

---

# Decision

We chose to create a `ContextBuilder`.

The component will be responsible for building the complete context to be sent to the AI model.

It ceases to be just a file reader and starts acting as a context engineer.

---

# Consequences

In the future, the ContextBuilder may incorporate:

- Markdown documents;
- PDFs;
- images converted to text;
- meeting notes;
- knowledge bases;
- templates;
- Security by Design;
- LGPD;
- glossaries;
- organizational standards.

No other component will need to know about these sources.

---

# Principle Created

**Context is a system asset.**

Context is not a consequence of documents.

It is a product built by PM OS.

---

# Sprint Insight

One of the main discoveries of this sprint was realizing that Context Engineering plays a more important role than Prompt Engineering.

Prompts guide the model.

Context determines response quality.

PM OS now adopts Context Engineering as one of the pillars of its architecture.
