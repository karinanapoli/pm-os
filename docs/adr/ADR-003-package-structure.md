# ADR-003 — Infrastructure Layer for AI Providers

## Status

Accepted

---

# Context

PM OS needs to generate artifacts using language models.

During the first Sprints, we used a `FakeAIClient` to validate the pipeline without depending on a real LLM.

With Sprint 003, we started integrating Ollama as the first real AI provider.

However, PM OS must not depend directly on Ollama, OpenAI, Claude, Gemini, or any other specific provider.

Workflows should depend only on an abstract capability:

> generate text from a prompt.

---

# Decision

We created an `AIClient` contract at:

```text
src/pm_os/contracts/ai_client.py
```
