# ADR-001 — O PM OS terá um Core independente do MCP

**Status:** Aceito

**Data:** Sprint 001

---

# Contexto

No início do projeto, a ideia era construir um servidor MCP capaz de executar workflows para Product Managers.

Durante a Sprint 001 percebemos que concentrar toda a lógica dentro do MCP faria com que a arquitetura ficasse fortemente acoplada ao protocolo.

Isso dificultaria:

- testes;
- reutilização;
- evolução do projeto;
- integração com outras interfaces.

Precisávamos decidir onde a lógica principal deveria viver.

---

# Opções consideradas

## Opção A

Toda a lógica dentro do MCP.

Fluxo:

Continue

↓

MCP

↓

Código

### Vantagens

- implementação inicial mais rápida.

### Desvantagens

- alto acoplamento;
- difícil reutilização;
- difícil testar;
- impossível criar CLI sem duplicar código.

---

## Opção B

Criar um Core independente.

Fluxo:

Interface

↓

MCP

↓

PM OS Core

↓

Workflows

↓

Domínio

### Vantagens

- arquitetura modular;
- reutilização;
- testes independentes;
- possibilidade de criar CLI;
- possibilidade de criar interface web;
- possibilidade de trocar Continue por outra interface.

### Desvantagens

- exige uma camada extra.

---

# Decisão

Optamos pela Opção B.

Todo o conhecimento do PM OS ficará dentro do PM OS Core.

O MCP será apenas uma camada responsável por expor ferramentas.

O Core não conhecerá MCP.

---

# Consequências

Esta decisão permite que, no futuro, o mesmo Core seja utilizado por:

- MCP
- CLI
- API
- Interface Web
- Continue
- OpenCode
- Claude Desktop
- Cursor

Sem alterações na lógica de negócio.

---

# Princípio criado

**O Core nunca dependerá da interface.**

As interfaces dependerão do Core.

Esse princípio passa a orientar toda a arquitetura do PM OS.