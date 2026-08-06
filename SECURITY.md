# Política de segurança 

## Versões suportadas

O projeto está em fase inicial. Correções de segurança são aplicadas à branch
`main`.

## Como reportar

Não abra uma issue pública contendo credenciais, dados pessoais ou instruções
de exploração. Use a opção **Report a vulnerability** na aba Security do
repositório:

https://github.com/karinanapoli/pm-os/security/advisories/new

Inclua o impacto, os passos mínimos para reprodução e, quando possível, uma
sugestão de correção. Evite acessar dados que não sejam seus.

## Escopo de dados

Por padrão, o workspace fica no computador do usuário. Ao selecionar OpenAI,
Anthropic ou um provedor customizado, o contexto escolhido é enviado ao
respectivo serviço. O modo Demo não envia conteúdo a provedores externos.

## Conexões MCP locais

Conexões MCP por HTTP são o padrão. O transporte `stdio` pode iniciar processos
no computador que executa o PM Studio e, por isso, fica desativado por padrão.
Somente o administrador da instalação deve habilitá-lo, definindo
`PM_OS_ENABLE_STDIO_MCP=1` no ambiente do servidor. Não habilite esse recurso
em uma instalação compartilhada sem isolamento adicional do processo.
