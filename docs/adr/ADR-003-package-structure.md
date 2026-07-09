# ADR-003 — Camada de Infraestrutura para Provedores de IA

## Status

Aceita

---

# Contexto

O PM OS precisa gerar artefatos utilizando modelos de linguagem.

Durante as primeiras Sprints, utilizamos um `FakeAIClient` para validar o pipeline sem depender de um LLM real.

Com a Sprint 003, passamos a integrar o Ollama como primeiro provedor real de IA.

Entretanto, o PM OS não deve depender diretamente do Ollama, OpenAI, Claude, Gemini ou qualquer outro provedor específico.

Os Workflows devem depender apenas de uma capacidade abstrata:

> gerar texto a partir de um prompt.

---

# Decisão

Criamos um contrato `AIClient` em:

```text
src/pm_os/contracts/ai_client.py