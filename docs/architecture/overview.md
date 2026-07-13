# PM OS — Architecture Overview

> "A arquitetura do PM OS foi projetada para transformar conhecimento em capacidades reutilizáveis, permitindo que Product Managers utilizem Inteligência Artificial de forma estruturada, escalável e independente de ferramentas específicas."

---

# Objetivo

O PM OS (Product Manager Operating System) é uma plataforma open source de AI Product Engineering.

Seu propósito é apoiar Product Managers durante todo o ciclo de vida de uma iniciativa, organizando conhecimento, executando workflows e gerando artefatos de produto de forma consistente.

O objetivo do projeto não é apenas integrar um Large Language Model (LLM), mas construir um sistema capaz de evoluir continuamente, mantendo baixo acoplamento, alta coesão e uma arquitetura simples de compreender.

---

# Visão Geral da Arquitetura

O PM OS é composto por três grandes blocos:

1. Interfaces de utilização
2. PM OS Core
3. Workspace

Cada bloco possui responsabilidades bem definidas.

```text
                        Usuário
                           │
                           ▼
        Continue • CLI • MCP • Web (futuro)
                           │
                           ▼
──────────────────────────────────────────────────
                    PM OS Core
──────────────────────────────────────────────────

        Workflows
             │
             ▼
     Initiative Repository
             │
             ▼
      Context Builder
             │
             ▼
      Prompt Builder
             │
             ▼
     AI Client (Contract)
             │
             ▼
 Infrastructure (Ollama, OpenAI...)
             │
             ▼
      Markdown Writer

──────────────────────────────────────────────────
                     Workspace
──────────────────────────────────────────────────

Initiatives
Templates
Knowledge
Configuration
```

---

# Princípios Arquiteturais

Toda decisão arquitetural do PM OS é guiada pelos seguintes princípios.

## Contexto antes de Prompt

Prompts são descartáveis.

Contexto é um ativo permanente.

O PM OS investe na organização e consolidação do contexto antes da interação com qualquer modelo de IA.

---

## AI é uma Dependência

Modelos de IA são serviços externos.

O domínio do PM OS nunca depende diretamente de uma implementação específica.

Hoje utilizamos Ollama.

Amanhã poderemos utilizar OpenAI, Azure OpenAI, Claude ou qualquer outro provedor.

---

## Core First

Toda regra de negócio pertence ao PM OS Core.

Interfaces, MCPs ou aplicações externas nunca implementam lógica de domínio.

---

## Baixo Acoplamento

Os componentes se comunicam através de contratos (Protocols).

Isso permite substituir implementações sem alterar os workflows.

---

## Alta Coesão

Cada componente possui apenas uma responsabilidade.

Essa separação facilita manutenção, testes e evolução da plataforma.

---

## Evolução Incremental

O PM OS evolui por pequenas entregas contínuas.

Cada Sprint busca fortalecer a arquitetura antes de adicionar novas capacidades.

---

# Organização do PM OS Core

O Core concentra toda a inteligência da plataforma.

Sua estrutura atual é organizada da seguinte forma:

```text
src/
└── pm_os/
    ├── contracts/
    ├── domain/
    ├── infrastructure/
    ├── repositories/
    ├── workflows/
    ├── writers/
    ├── templates/
    ├── bootstrap.py
    └── context_builder.py
```

Cada diretório possui uma responsabilidade específica.

| Componente | Responsabilidade |
|------------|------------------|
| `contracts/` | Define os contratos (Protocols) utilizados pela aplicação. |
| `domain/` | Contém os conceitos centrais do domínio do PM OS. |
| `repositories/` | Recupera informações do Workspace. |
| `workflows/` | Orquestra a execução das capacidades da plataforma. |
| `infrastructure/` | Implementações concretas de serviços externos (Ollama, Logging, etc.). |
| `writers/` | Responsável por persistir artefatos gerados. |
| `templates/` | Templates utilizados pelos workflows. |

---

# O Domínio

O conceito central do PM OS é a **Initiative**.

Uma Initiative representa um problema de negócio ou uma oportunidade de produto.

Ela concentra todo o conhecimento relacionado ao seu ciclo de vida.

Uma Initiative pode conter:

- documentos de discovery;
- atas de reunião;
- pesquisas;
- requisitos;
- PRDs;
- backlogs;
- roadmaps;
- RFCs;
- métricas;
- decisões arquiteturais.

Essa decisão foi formalizada na **ADR-004 — Workspace Orientado a Iniciativas**.

---

# Workspace

O Workspace representa a área de trabalho do usuário.

Ele contém todas as iniciativas e os artefatos produzidos pelo PM OS.

Estrutura atual:

```text
workspace/
└── initiatives/
    └── INT-0001-consulta-inteligente-fornecedores/
        ├── context/
        ├── artifacts/
        ├── logs/
        └── metadata.yaml
```

## Context

Armazena todo o conhecimento bruto utilizado pelos workflows.

Exemplos:

- Discovery
- Entrevistas
- Reuniões
- Notas
- Documentação técnica

---

## Artifacts

Contém todos os documentos gerados pelo PM OS.

Exemplos:

- PRD
- Backlog
- Roadmap
- RFC
- Executive Summary

---

## Metadata

Representa a identidade da Initiative.

No futuro armazenará informações como:

- identificador;
- responsável;
- status;
- tags;
- workflows executados;
- artefatos gerados.

---

## Logs

Armazena o histórico de execução dos workflows relacionados à Initiative.

---

# Fluxo de Execução

O principal workflow do PM OS segue a sequência abaixo:

```text
Usuário
    │
    ▼
Interface
    │
    ▼
Workflow
    │
    ▼
Initiative Repository
    │
    ▼
Context Builder
    │
    ▼
Prompt Builder
    │
    ▼
AI Client (Contract)
    │
    ▼
Infrastructure
(Ollama, OpenAI...)
    │
    ▼
Markdown Writer
    │
    ▼
Artifact
```

Cada componente possui uma única responsabilidade e pode evoluir independentemente.

---

# Capabilities

O PM OS é organizado em torno de capacidades reutilizáveis.

Cada capacidade representa um workflow completo de produto.

Exemplos planejados:

- Create PRD
- Create Backlog
- Create Roadmap
- Create RFC
- Executive Summary
- AI Review
- Security Review

Todas reutilizam a mesma arquitetura do Core.

---

# Benefícios da Arquitetura

A arquitetura foi desenhada para proporcionar:

- evolução incremental;
- baixo acoplamento;
- alta coesão;
- facilidade de testes;
- reutilização de componentes;
- independência entre domínio e infraestrutura;
- suporte a múltiplos provedores de IA;
- facilidade de contribuição da comunidade open source.

---

# Próximos Passos

A arquitetura continuará evoluindo conforme novas capacidades forem adicionadas.

Entre os próximos temas previstos estão:

- camada de configuração centralizada;
- testes de integração;
- Template Engine;
- múltiplos provedores de IA;
- Vector Store;
- observabilidade avançada;
- CLI oficial do PM OS.

---

# Resumo

O PM OS não é apenas um gerador de documentos.

Ele é uma plataforma de AI Product Engineering construída para transformar conhecimento em capacidades reutilizáveis.

Sua arquitetura foi projetada para refletir o modelo mental de Product Managers, mantendo uma clara separação entre domínio, infraestrutura e interfaces.

Essa abordagem permite que o projeto evolua de forma incremental, mantendo simplicidade, escalabilidade e facilidade de colaboração.