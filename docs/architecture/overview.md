# PM OS Architecture Overview

> "A arquitetura é a forma como organizamos responsabilidades para que o sistema possa evoluir sem perder simplicidade."

---

# Visão Geral

O PM OS foi projetado como um framework de AI Product Engineering.

O objetivo não é apenas integrar um Large Language Model, mas criar um sistema capaz de organizar conhecimento, executar workflows e apoiar Product Managers durante todo o ciclo de desenvolvimento de produtos.

Para isso, adotamos uma arquitetura baseada em componentes independentes e responsabilidades bem definidas.

Cada camada do sistema possui uma única função.

Essa separação permite que novas funcionalidades sejam adicionadas sem alterar a estrutura existente.

---

# Arquitetura em Camadas

```text
                    User

                     │

                     ▼

      Continue • OpenCode • CLI • Web

                     │

                     ▼

               MCP Server Layer

                     │

                     ▼

                PM OS Core Layer

      ┌────────────────────────────────┐

      │                                │

Repositories      Builders      Workflows

AI Clients        Writers       Domain Models

      │                                │

      └────────────────────────────────┘

                     │

                     ▼

            Workspace / Knowledge
```

---

# Camada 1 — Interface

A camada de interface representa todas as formas pelas quais um usuário pode utilizar o PM OS.

Exemplos:

- Continue
- OpenCode
- CLI
- Interface Web (futuro)

Esta camada nunca implementa regras de negócio.

Seu único objetivo é iniciar um workflow.

---

# Camada 2 — MCP

O MCP atua como uma ponte entre as interfaces e o PM OS Core.

Seu papel é expor ferramentas como:

- create_prd
- create_backlog
- create_rfc
- security_review
- executive_summary

O MCP não possui inteligência própria.

Ele apenas recebe solicitações e encaminha para o Core.

---

# Camada 3 — PM OS Core

O PM OS Core é o coração do sistema.

Toda a lógica de negócio reside aqui.

O Core contém componentes especializados, cada um responsável por uma parte do workflow.

Exemplos:

- Domain Models
- Repositories
- Context Builders
- Prompt Builders
- AI Clients
- Writers
- Workflows

O Core não conhece:

- Continue
- OpenCode
- MCP
- Interface Web

Isso garante independência entre a lógica do sistema e a forma como ele é utilizado.

---

# Camada 4 — Workspace

O Workspace representa o conhecimento utilizado pelo PM OS.

Inclui:

- Features
- Templates
- Skills
- Knowledge Base
- Configurações

O Workspace é tratado como uma fonte de informação.

Ele nunca executa lógica de negócio.

---

# Fluxo Principal

O principal workflow do PM OS seguirá a seguinte sequência:

```text
Usuário

↓

Interface

↓

MCP

↓

Workflow

↓

Repository

↓

ContextBuilder

↓

PromptBuilder

↓

AIClient

↓

Writer

↓

Workspace
```

Cada componente possui apenas uma responsabilidade.

Nenhum componente executa tarefas pertencentes a outro.

---

# Princípios Arquiteturais

A arquitetura do PM OS é guiada pelos seguintes princípios.

## Core First

Toda lógica de negócio deve permanecer no PM OS Core.

Interfaces nunca implementam regras de domínio.

---

## Low Coupling

Componentes devem depender de contratos simples.

Sempre que possível, mudanças em um componente não devem impactar os demais.

---

## High Cohesion

Cada componente possui apenas uma responsabilidade claramente definida.

---

## Context Engineering

O PM OS prioriza a construção de contexto antes da geração de prompts.

Contexto é considerado um ativo do sistema.

---

## AI as a Dependency

Modelos de IA são dependências externas.

O sistema deve continuar organizado independentemente do modelo utilizado.

---

## Replaceable Components

Qualquer componente poderá ser substituído sem alterar a arquitetura.

Exemplos:

- Ollama → OpenAI
- Continue → Cursor
- MCP → API REST

---

# Objetivos da Arquitetura

Esta arquitetura foi desenhada para permitir:

- evolução incremental;
- facilidade de testes;
- reutilização de componentes;
- suporte a múltiplas interfaces;
- integração com diferentes modelos de IA;
- manutenção simples;
- contribuição da comunidade open source.

---

# Evolução Esperada

O MVP será composto por um único workflow:

```
create_prd
```

Com a evolução do projeto, novos workflows serão adicionados utilizando exatamente a mesma arquitetura.

Exemplos:

- create_backlog
- create_roadmap
- create_rfc
- security_review
- ai_review
- executive_summary

A arquitetura foi planejada para que esses novos workflows reutilizem os componentes existentes, reduzindo duplicação de código e mantendo consistência em todo o framework.

---

# Resumo

O PM OS não é um chatbot.

O PM OS é um framework de AI Product Engineering.

Sua arquitetura foi desenhada para separar claramente:

- interfaces;
- protocolos;
- lógica de negócio;
- inteligência artificial;
- armazenamento de conhecimento.

Essa separação garante que o projeto permaneça simples, modular e escalável conforme novas funcionalidades forem sendo adicionadas.