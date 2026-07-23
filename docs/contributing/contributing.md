# Como contribuir

Contribuições de pessoas de produto e tecnologia são bem-vindas. Você não
precisa escrever código: documentação, exemplos, pesquisas e relatos de uso
também melhoram o PM Studio.

## Preparação

1. Crie um fork e uma branch pequena.
2. Instale Python 3.9 ou superior.
3. Execute `python -m venv .venv`.
4. Ative o ambiente e rode `python -m pip install -e ".[dev]"`.
5. Execute `pytest` antes e depois da mudança.

## Boas contribuições

- Explique qual problema de uma PM está sendo resolvido.
- Prefira mudanças pequenas, com testes e documentação.
- Preserve a separação entre domínio, infraestrutura e interface.
- Nunca inclua chaves, documentos internos ou dados pessoais nos exemplos.
- Registre decisões arquiteturais relevantes em um ADR.

## Pull request

Descreva problema, solução, como testar, riscos de privacidade e screenshots
quando houver mudança de interface. Ao participar, você concorda com o
[Código de Conduta](../../CODE_OF_CONDUCT.md).
