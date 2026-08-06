# PM Studio

Um laboratório open source para Product Managers aprenderem IA enquanto
transformam informações dispersas em contexto, decisões e documentos
rastreáveis.

O PM Studio não é um chatbot nem uma coleção de prompts. Ele organiza cada
iniciativa em um workspace e executa workflows como geração e validação de PRD,
mantendo a pessoa responsável pelo produto no controle.

## O que funciona hoje

- Iniciativas com documentos de contexto e histórico de artefatos.
- Especificação de produto guiada, versionada e opcional.
- Decisões, aprovação e backlog rastreável sem remover o fluxo rápido de PRD.
- Exportação governada do backlog com seleção, preview, confirmação e pacote
  portátil para GitHub Issues, Linear e Plane.
- Criação governada dos itens via ferramentas MCP habilitadas para escrita,
  com confirmação explícita, idempotência e resultado por história.
- Memória transversal de decisões com estado e condição explícita
  **“revisitar se”**.
- Mapa da Iniciativa conectando sinais, fontes, especificação, decisões e
  entregáveis.
- Central de Sinais para relacionar feedbacks, pesquisas, métricas e relatórios
  às iniciativas.
- Extração revisável de sinais a partir de PDF, Markdown e TXT, com
  processamento local por padrão.
- Geração, validação de PRD e consulta a documentos.
- Ollama local, OpenAI, Anthropic e provedores compatíveis com OpenAI.
- **Modo Demo**, sem chave, custo ou envio de dados a uma IA externa.
- Interface em português e inglês.
- Servidor MCP para consultar iniciativas, contexto e PRDs.

> O projeto está em desenvolvimento ativo. Não trate documentos gerados ou
> notas de validação como decisões automáticas: revise fontes e inferências.

## Experimente em cinco minutos

Requisitos: Python 3.10 ou superior.

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

### Exposição em rede

O padrão `127.0.0.1` mantém o PM Studio acessível apenas no computador local.
Antes de publicá-lo em uma rede, defina `PM_OS_ENV=production` e um
`PM_OS_SECRET` longo e aleatório.

Se houver um proxy reverso confiável entre as pessoas usuárias e o PM Studio,
defina `PM_OS_TRUSTED_PROXY_COUNT` com a quantidade exata de proxies no caminho.
O valor padrão é `0`: cabeçalhos de IP enviados pelo navegador são ignorados
para impedir que o limite de tentativas de login seja contornado.

Defina também `PM_OS_ALLOWED_HOSTS` com os domínios aceitos, separados por
vírgula, e `PM_OS_PUBLIC_URL` com o endereço HTTPS exibido nos links enviados
por e-mail. Exemplo:

```bash
PM_OS_ALLOWED_HOSTS=pm.exemplo.com
PM_OS_PUBLIC_URL=https://pm.exemplo.com
```

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

Cada iniciativa pode continuar no **modo rápido** ou usar o **modo guiado
(Beta)**:

```text
sinais → evidências → especificação → esclarecimentos → aprovação → PRD/backlog
```

Veja [Central de Sinais](docs/product/signals.md) e
[Especificação Guiada](docs/product/guided-specification.md). A
[Memória de Decisões](docs/product/decision-memory.md) conecta escolhas entre
iniciativas. O [Mapa da Iniciativa](docs/product/initiative-map.md) apresenta
a rastreabilidade de cada iniciativa em uma única visão.

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

Em **Configurações → Fontes externas**, também é possível cadastrar servidores
MCP de terceiros:

- **HTTP** para servidores remotos usando Streamable HTTP;
- **stdio** para iniciar um servidor como processo local, com comando,
  argumentos e variáveis de ambiente.

O cadastro testa e descobre capacidades, mas não executa ferramentas de escrita
automaticamente. Variáveis de ambiente e credenciais são criptografadas no
arquivo de configuração. Consulte
[Conexões MCP](docs/product/mcp-connections.md).

No Assistente da iniciativa, ferramentas MCP HTTP descobertas e marcadas como
somente leitura podem ser chamadas explicitamente por mensagem. Resultados são
limitados, tratados como dados externos não confiáveis e registrados no
histórico da conversa.

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
