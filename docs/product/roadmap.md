# PM OS — Product Roadmap

> "O Roadmap do PM OS é organizado por capacidades da plataforma. Cada capacidade representa uma evolução funcional reutilizável para Product Managers."

---

# Visão

Construir uma plataforma open source de AI Product Engineering capaz de apoiar Product Managers durante todo o ciclo de desenvolvimento de produtos.

A evolução do PM OS acontece por capacidades incrementais, reutilizando uma arquitetura comum e mantendo baixo acoplamento entre seus componentes.

---

# Capacidades

| Capability | Status | Sprint |
|------------|--------|---------|
| Foundation | ✅ Concluída | Sprint 001 |
| Core Architecture | ✅ Concluída | Sprint 002 |
| Create PRD | ✅ Concluída | Sprint 003 |
| Configuration Layer | 🟡 Planejada | Sprint 004 |
| Integration Tests | 🟡 Planejada | Sprint 004 |
| Create Backlog | 🟡 Planejada | Sprint 005 |
| Template Engine | 🟡 Planejada | Sprint 005 |
| Create Roadmap | 🔵 Backlog | Sprint 006 |
| Executive Summary | 🔵 Backlog | Sprint 006 |
| AI Review | 🔵 Backlog | Sprint 007 |
| Security Review | 🔵 Backlog | Sprint 007 |
| RFC Generator | 🔵 Backlog | Sprint 008 |
| Vector Store | ⚪ Futuro | TBD |
| Knowledge Graph | ⚪ Futuro | TBD |
| Multi Provider AI | ⚪ Futuro | TBD |
| Web Interface | ⚪ Futuro | TBD |
| MCP Server | ⚪ Futuro | TBD |

---

# Próxima Sprint

## Sprint 004

### Epic

Platform Evolution

### Objetivos

- Implementar camada centralizada de configuração.
- Criar testes de integração.
- Melhorar a CLI.
- Preparar a plataforma para múltiplos provedores de IA.

---

# Visão de Longo Prazo

O PM OS deverá evoluir para uma plataforma composta por diversas capacidades reutilizáveis.

Cada nova capability deverá reutilizar os componentes existentes do Core, preservando a arquitetura construída nas primeiras Sprints.

A evolução do projeto seguirá os princípios de:

- Context Engineering;
- AI as a Dependency;
- Domain-Driven Design;
- Arquitetura orientada a capacidades;
- Evolução incremental.

---

# Critérios para Novas Capacidades

Uma nova capability somente será adicionada quando:

- reutilizar a arquitetura existente;
- representar um caso de uso completo;
- possuir valor para Product Managers;
- não aumentar o acoplamento da plataforma;
- respeitar os princípios arquiteturais do PM OS.