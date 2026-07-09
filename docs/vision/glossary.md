# PM OS Glossary

Este documento reúne os principais conceitos utilizados pelo PM OS.

Seu objetivo é criar uma linguagem comum entre Product Managers, engenheiros e contribuidores.

---

# AI Client

Componente responsável por conversar com um modelo de Inteligência Artificial.

Exemplos futuros:

- Ollama
- OpenAI
- Gemini
- Claude

---

# Builder

Componente responsável por transformar uma entrada em outra representação.

Exemplos:

ContextBuilder

PromptBuilder

---

# Context

Conjunto organizado de informações preparado para ser enviado ao modelo de IA.

Contexto não é apenas a soma de documentos.

É um ativo construído pelo sistema.

---

# Context Engineering

Disciplina responsável por construir contexto de alta qualidade para modelos de IA.

É um dos pilares do PM OS.

---

# Core

Camada central do PM OS.

Contém toda a lógica de negócio.

Nunca depende de interfaces externas.

---

# Domain Model

Objeto que representa um conceito do domínio do Product Management.

Exemplo:

Feature

---

# Feature

Unidade de trabalho do PM OS.

Uma Feature pode conter documentos, requisitos, atas, APIs, imagens e qualquer outro insumo relacionado ao desenvolvimento de um produto.

---

# MCP

Model Context Protocol.

Camada responsável por disponibilizar ferramentas do PM OS para diferentes interfaces.

No PM OS o MCP nunca contém regras de negócio.

---

# PM OS Core

Núcleo do framework.

Onde vivem:

- Repositories
- Builders
- Workflows
- AI Clients
- Writers
- Domain Models

---

# Prompt

Conjunto de instruções enviado ao modelo de IA.

O Prompt informa o que o modelo deve fazer.

---

# Prompt Engineering

Técnicas utilizadas para estruturar prompts.

No PM OS o Prompt Engineering é considerado complementar ao Context Engineering.

---

# Repository

Componente responsável por acessar fontes de dados.

Exemplo:

FeatureRepository.

---

# Workflow

Sequência organizada de componentes que executam uma tarefa.

Exemplo:

create_prd

↓

FeatureRepository

↓

ContextBuilder

↓

PromptBuilder

↓

AIClient

↓

MarkdownWriter

---

# Workspace

Conjunto de arquivos utilizados pelo PM OS.

Inclui:

- Features
- Templates
- Skills
- Knowledge
- Configurações

O Workspace representa a principal fonte de conhecimento do sistema.

---

# Writer

Componente responsável por persistir resultados.

Exemplo:

MarkdownWriter.