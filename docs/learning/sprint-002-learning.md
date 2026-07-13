# Sprint 002 Learning Journal

## O que aprendemos

Durante esta Sprint consolidamos diversos conceitos fundamentais de arquitetura.

### Workflows

Aprendemos que Workflows representam casos de uso.

Eles orquestram componentes.

Não implementam regras de negócio específicas.

---

### Dependency Injection

Aprendemos a receber dependências pelo construtor.

Isso reduz acoplamento.

---

### Protocols

Criamos contratos utilizando typing.Protocol.

O Core agora depende de comportamento e não de implementações.

---

### Composition Root

Introduzimos o Bootstrap.

Toda montagem da aplicação passa a ocorrer em um único lugar.

---

### Testes

Criamos os primeiros testes unitários do projeto.

Componentes testados:

- AIClient
- PromptBuilder
- MarkdownWriter

---

### Produto

A maior descoberta da Sprint foi perceber que o PM OS não é um gerador de PRDs.

Ele é um Sistema Operacional para iniciativas de produto.

O verdadeiro ativo do sistema é o contexto.