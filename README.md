# PM Studio

Um laboratório open source para Product Managers aprenderem IA enquanto
transformam informações dispersas em contexto, decisões e documentos
rastreáveis.

O PM Studio não é um chatbot nem uma coleção de prompts. Ele organiza cada
iniciativa em um workspace e executa workflows como geração e validação de PRD,
mantendo a pessoa responsável pelo produto no controle.

## O que funciona hoje

- Iniciativas com documentos de contexto e histórico de artefatos.
- Geração, validação de PRD e consulta a documentos.
- Ollama local, OpenAI, Anthropic e provedores compatíveis com OpenAI.
- **Modo Demo**, sem chave, custo ou envio de dados a uma IA externa.
- Interface em português e inglês.
- Servidor MCP para consultar iniciativas, contexto e PRDs.

> O projeto está em desenvolvimento ativo. Não trate documentos gerados ou
> notas de validação como decisões automáticas: revise fontes e inferências.

## Experimente em cinco minutos

Requisitos: Python 3.9 ou superior.

```bash
git clone https://github.com/karinanapoli/pm-os.git
cd pm-os
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -e .
pm-studio
```

Abra `http://127.0.0.1:8000` e crie sua conta. O **Modo Demo** já vem
selecionado: use o início rápido para percorrer o fluxo completo sem configurar
uma IA. Para ler PDFs, instale `python -m pip install -e ".[pdf]"`.

## Escolha de privacidade

| Modo | Custo externo | Para onde vai o contexto? |
|---|---:|---|
| Demo | Nenhum | Não sai do PM Studio |
| Ollama | Nenhum | Modelo local configurado |
| OpenAI/Anthropic | Conforme o provedor | API do provedor escolhido |
| Customizado | Conforme o provedor | URL configurada |

Nunca coloque segredos, credenciais ou dados pessoais desnecessários no
workspace. Consulte as regras da sua organização e a política do provedor.

## Como o fluxo funciona

```text
fontes → contexto → workflow → modelo → PRD + validação humana
```

Comece por [Visão](docs/vision/vision.md),
[Manifesto](docs/vision/manifesto.md),
[Jornada](docs/product/user_journey.md),
[Arquitetura](docs/architecture/overview.md),
[ADRs](docs/adr/), [Aprendizados](docs/learning/) e
[Roadmap](docs/product/roadmap.md).

## MCP

Com Python 3.10+, instale `python -m pip install -e ".[mcp]"` e execute
`python mcp/server.py`. O servidor expõe `list_initiatives`,
`get_initiative_context` e `get_initiative_prd`, usando o mesmo `workspace/`.

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
pytest
ruff check --select E9,F63,F7,F82 src mcp scripts tests
```

Veja [como contribuir](docs/contributing/contributing.md), o
[Código de Conduta](CODE_OF_CONDUCT.md) e a [Política de
Segurança](SECURITY.md).

## Licença

[MIT](LICENSE).
