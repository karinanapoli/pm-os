# Avaliação de arquitetura e segurança — agosto de 2026

## Resumo executivo

O PM Studio tem uma base adequada para um produto local: domínio, repositórios,
serviços de aplicação e integrações estão separados em módulos; o conteúdo em
Markdown é sanitizado; credenciais persistidas são criptografadas; senhas usam
Argon2id; uploads, SSRF, CSRF, host header e jobs por usuário/squad possuem
controles dedicados.

O principal débito arquitetural é o `web/app.py`, com mais de 3.300 linhas, 88
rotas e composição de infraestrutura, autorização, apresentação e casos de uso
no mesmo módulo. Isso aumenta o raio de impacto das mudanças e dificulta aplicar
políticas de autorização de forma uniforme.

## Achados priorizados

| Prioridade | Achado | Impacto | Tratamento |
|---|---|---|---|
| Crítica | MCP `stdio` aceitava comando configurável e o executava no host | Execução de código no servidor por usuário com acesso às configurações | Corrigido: bloqueado por padrão e liberado somente por variável de ambiente do operador |
| Média | Logout era uma operação mutável via GET | Logout forçado por navegação externa | Corrigido: rota POST protegida por CSRF |
| Média | Cabeçalhos de defesa eram aplicados apenas a HTML | Downloads e respostas auxiliares tinham proteção inconsistente | Corrigido: `nosniff`, anti-frame, política de referência, permissões e isolamento em todas as respostas; HSTS em HTTPS de produção |
| Média | Configurações e integrações são globais, embora o produto já tenha usuários e squads | Um modelo multiusuário exige papéis administrativos explícitos | Corrigido: primeiro usuário é administrador, instalações antigas migram com segurança e demais usuários recebem 403 |
| Média | CSP ainda permite scripts e estilos inline | Uma futura falha de injeção teria impacto maior | Pendente: mover scripts inline para arquivos estáticos e adotar nonce ou hashes |
| Baixa | Dependências usam intervalos amplos e não há auditoria de CVEs no pipeline | Atualizações podem introduzir regressões ou vulnerabilidades conhecidas | Pendente: lock reproduzível e verificação automática de advisories no CI |
| Baixa | O lint registra dívida histórica ampla | Sinal/ruído reduzido e manutenção mais cara | Pendente: baseline e adoção incremental por arquivos alterados |

## Direção arquitetural recomendada

Extrair o módulo web por capacidades, mantendo serviços e repositórios atuais:

- `routes/auth.py`: sessão, cadastro, verificação e recuperação;
- `routes/initiatives.py`: iniciativa, contexto, decisões e entregáveis;
- `routes/generation.py`: geração, validação e jobs;
- `routes/integrations.py`: provedores, MCP e configurações;
- dependências centrais para identidade, squad e autorização administrativa;
- composição dos routers em um `create_app()` pequeno e testável.

A migração deve ser incremental, um conjunto de rotas por vez, preservando os
testes ponta a ponta existentes. O primeiro recorte foi concluído: políticas de
acesso globais foram extraídas para `access_control.py` e as rotas de provedores
customizados para `provider_routes.py`, estabelecendo o padrão de router com
dependências explícitas para os próximos recortes.

## Escopo do pentest controlado

Foram exercitados autenticação e isolamento de sessão, CSRF, host header,
escopo de jobs, travessia de diretórios em iniciativas e uploads, limites de
arquivo, SSRF e redirects autenticados, exposição de segredos, download antes
de aprovação e tentativa de cadastrar MCP `stdio` sem autorização do operador.

Nenhum dado da iniciativa real foi modificado. O teste visual em localhost não
pôde ser concluído porque a política administrativa do navegador não autorizou
o acesso; os mesmos controles HTTP foram exercitados pela suíte isolada da
aplicação.
