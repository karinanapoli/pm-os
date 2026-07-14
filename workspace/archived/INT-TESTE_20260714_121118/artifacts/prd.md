**Requisitos Técnicos - Smart Supplier Query**

### **1. Overview**

Smart Supplier Query é um sistema de consulta inteligente de fornecedores para o setor de supply chain brasileiro. Ele integra dados públicos e internos para fornecer uma experiência de consultas simples, rápida e eficiente.

### **2. Problema**

O problema principal é que os fornecedores brasileiros precisam realizar tarefas burocráticas e manualis para consultar os dados necessários para a análise de supply chain. Isso gera tempo extra e aumenta o tempo de recuperação.

### **3. Objectivos**

* Desenvolver um sistema de consultas inteligentes que unifique dados públicos e internos
* Fornecer uma experiência de consulta rápida e eficiente para fornecedores
* Garantir a integração do sistema com todos os sistemas existentes no setor
* Implementar uma solução de história completa com linha do tempo

### **4. Out of Scope**

* Desenvolver um sistema de recurso de documentação para fornecedores
* Integração com ERP e CRM
* Desenvolvimento de recursos adicionais (como ferramentas de análise)

### **5. Personas / Usuários**

**Fornecedores:**

* Analistas de supply chain
* Procurement Leads
* Analistas de análise de supply chain

### **6. Functional Requirements**

1. Consulta unificada:
 * CNPJ, CPF e nome fantasia por uma única interface
2. Histórico completo:
 * Linha do tempo com todas as alterações
3. Alertas proativos:
 * Documentação vencida
4. Integração com sistemas existentes:
 * ERP, CRM, etc.
5. Gestão de dados:
 * Tratamento e armazenamento dos dados

### **7. Non-Functional Requirements**

1. Performance:
 * Tempo de recuperação < 2 segundos para consultas simples
 * Tempo de recuperação < 5 segundos para consultas com enrichment
2. Segurança:
 * TLS 1.3 em trânsito e logs de auditoria
3. Observabilidade:
 * Logs estruturados no Datadog
4. Cache:
 * Redis 7+
5. Integração:
 * API pública para integrações via API

### **8. Success Metrics**

* Número de usuários ativos: 10
* NPS > 30
* Tarifa mensal < R$ 3.000 (até 100 consultas simultâneas)
* ARR alvo:
 * Fim Fase 1: R$ 60.000
 * Fim Fase 2: R$ 360.000

### **9. Risks**

* Problemas de integração com sistemas existentes
* Dificuldade em obter dados de fornecedores
* Falta de recursos para desenvolver o sistema

### **10. Open Questions**

1. Como podemos melhorar a experiência de consultas para fornecedores?
2. Como podemos integrar nosso sistema com outros sistemas existentes no setor?
3. Como podemos lidar com dados dispersos e sem histórico?