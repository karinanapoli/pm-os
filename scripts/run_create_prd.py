from pm_os.bootstrap import create_prd_workflow
from pm_os.infrastructure.ai.clients.ollama_client import OllamaConnectionError


OUTPUT_PATH = (
    "workspace/initiatives/"
    "INT-0001-smart-supplier-query/"
    "artifacts/prd.md"
)


def main() -> None:
    workflow = create_prd_workflow()

    try:
        output_file = workflow.run(OUTPUT_PATH)

        print(f"\nPRD successfully created at:\n{output_file}")

    except OllamaConnectionError:
        print(
            "\nCould not connect to Ollama.\n\n"
            "Make sure the server is running with:\n\n"
            "ollama serve"
        )


if __name__ == "__main__":
    main()
