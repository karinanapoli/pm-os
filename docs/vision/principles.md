# PM OS Principles

Os princípios abaixo orientam todas as decisões arquiteturais e de produto do PM OS.

Quando existir dúvida entre duas soluções, estes princípios deverão prevalecer.

---

# 1. Context > Prompt

Sempre priorizamos a qualidade do contexto antes da qualidade do prompt.

Prompts orientam modelos.

Contexto determina a qualidade das respostas.

---

# 2. Workflows > Prompts

Nunca construir funcionalidades baseadas apenas em prompts.

Todo prompt deve fazer parte de um workflow.

---

# 3. AI is a Dependency

A IA é uma dependência do sistema.

Nunca o centro da arquitetura.

O PM OS deve continuar organizado mesmo que o modelo seja substituído.

---

# 4. Core First

Toda regra de negócio deve permanecer no PM OS Core.

Interfaces nunca implementam lógica de domínio.

---

# 5. Low Coupling

Componentes devem depender apenas do que realmente precisam conhecer.

Mudanças em um componente não devem impactar o restante do sistema.

---

# 6. High Cohesion

Cada componente possui apenas uma responsabilidade.

Se um componente começa a fazer muitas coisas, ele deve ser dividido.

---

# 7. Composition over Magic

Preferimos pequenos componentes especializados trabalhando juntos.

Evitamos componentes gigantes que fazem "tudo".

---

# 8. Learn by Building

Cada componente do PM OS deve ensinar algum conceito.

O projeto é também uma ferramenta de aprendizado.

---

# 9. Open Source by Design

Toda decisão deve considerar clareza, simplicidade e facilidade de contribuição.

O projeto deve ser acessível para novos contribuidores.

---

# 10. Security by Design

Segurança não é uma etapa do workflow.

Ela faz parte da arquitetura.

Sempre que possível, princípios de segurança devem estar presentes desde o início do desenvolvimento.

---

# 11. Document Decisions

Toda decisão arquitetural importante deve ser registrada através de um ADR.

Código muda.

Decisões permanecem.

---

# 12. Small Iterations

O PM OS evolui através de pequenas sprints.

Cada sprint deve entregar valor.

Cada sprint deve deixar o projeto melhor do que estava antes.