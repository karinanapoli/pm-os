# Requisitos Técnicos — Smart Supplier Query

## Stack Tecnológica
- **Backend**: Python 3.11+, FastAPI
- **Frontend**: Web Components (Lit) ou React
- **Banco de Dados**: PostgreSQL 15+
- **Cache**: Redis 7+
- **Busca**: Elasticsearch para indexação de fornecedores

## Integrações
1. **API Receita Federal** — consulta CNPJ
   - Rate limit: 3 req/s
   - Autenticação: API Key
2. **API Serasa** — score de crédito
   - Contrato anual
   - SLA: 99.5%
3. **Sistema Interno de Compras** (legado)
   - Banco SQL Server
   - View `v_fornecedores` já disponível

## Performance
- P95 < 2s para consulta simples
- P95 < 5s para consulta com enrichment
- Suportar 100 consultas simultâneas

## Segurança
- Todos os dados em trânsito: TLS 1.3
- Logs de auditoria para todas as consultas
- LGPD: dados de fornecedores são compartilháveis (contrato vigente)
- RBAC: 3 níveis de acesso (consulta, admin, auditor)

## Observabilidade
- Logs estruturados no Datadog
- Métricas: consultas/min, latência, erros
- Dashboard no Grafana para o time
