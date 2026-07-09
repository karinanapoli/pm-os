# ADR-002 — O PM OS utilizará Context Engineering em vez de Document Loading

**Status:** Aceito

**Data:** Sprint 001

---

# Contexto

Durante a implementação inicial do PM OS surgiu a necessidade de ler todos os documentos de uma Feature para enviá-los ao modelo de IA.

A primeira ideia foi criar um componente chamado `DocumentLoader`.

Entretanto, percebemos que essa responsabilidade seria muito maior do que apenas carregar arquivos.

Precisávamos decidir qual seria a verdadeira responsabilidade desse componente.

---

# Problema

Um Large Language Model não entende arquivos.

Ele entende contexto.

Enviar documentos diretamente para o modelo cria diversos problemas:

- documentos duplicados;
- informações irrelevantes;
- contexto desorganizado;
- desperdício de tokens;
- baixa qualidade das respostas.

Era necessário criar uma camada responsável por preparar esse contexto.

---

# Opções consideradas

## Opção A

Criar um DocumentLoader.

Responsabilidade:

- abrir arquivos;
- devolver texto.

### Vantagens

- implementação simples.

### Desvantagens

- pouca responsabilidade de negócio;
- não permite evolução futura;
- mistura infraestrutura com preparação de contexto.

---

## Opção B

Criar um ContextBuilder.

Responsabilidade:

- ler documentos;
- organizar informações;
- remover redundâncias;
- adicionar conhecimento complementar;
- aplicar templates;
- estruturar contexto para IA.

### Vantagens

- representa uma responsabilidade de domínio;
- separa infraestrutura da preparação para IA;
- facilita reutilização;
- permite crescimento do projeto.

### Desvantagens

- componente inicialmente mais abstrato.

---

# Decisão

Optamos por criar um `ContextBuilder`.

O componente será responsável por construir o contexto completo que será enviado ao modelo de IA.

Ele deixa de ser apenas um leitor de arquivos e passa a atuar como um engenheiro de contexto.

---

# Consequências

No futuro, o ContextBuilder poderá incorporar:

- documentos Markdown;
- PDFs;
- imagens convertidas em texto;
- atas de reunião;
- bases de conhecimento;
- templates;
- Security by Design;
- LGPD;
- glossários;
- padrões organizacionais.

Nenhum outro componente precisará conhecer essas fontes.

---

# Princípio criado

**Contexto é um ativo do sistema.**

O contexto não é uma consequência dos documentos.

Ele é um produto construído pelo PM OS.

---

# Insight da Sprint

Uma das principais descobertas desta sprint foi perceber que Context Engineering possui um papel mais importante do que Prompt Engineering.

Prompts orientam o modelo.

Contexto determina a qualidade da resposta.

O PM OS passa a adotar Context Engineering como um dos pilares da arquitetura.