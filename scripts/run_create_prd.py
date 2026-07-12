from pm_os.bootstrap import create_prd_workflow
from pm_os.infrastructure.ai.clients.ollama_client import OllamaConnectionError


OUTPUT_PATH = (
    "workspace/initiatives/"
    "INT-0001-consulta-inteligente-fornecedores/"
    "artifacts/prd.md"
)


def main() -> None:
    workflow = create_prd_workflow()

    try:
        output_file = workflow.run(OUTPUT_PATH)

        print(f"\nPRD criado com sucesso em:\n{output_file}")

    except OllamaConnectionError:
        print(
            "\nNão foi possível conectar ao Ollama.\n\n"
            "Verifique se o servidor está rodando com:\n\n"
            "ollama serve"
        )


if __name__ == "__main__":
    main()