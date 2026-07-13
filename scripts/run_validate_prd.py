from pm_os.bootstrap import create_validate_prd_workflow
from pm_os.infrastructure.ai.clients.ollama_client import OllamaConnectionError


PRD_PATH = (
    "workspace/initiatives/"
    "INT-0001-smart-supplier-query/"
    "artifacts/prd.md"
)

REPORT_PATH = (
    "workspace/initiatives/"
    "INT-0001-smart-supplier-query/"
    "artifacts/prd-validation.md"
)


def main() -> None:
    workflow = create_validate_prd_workflow()

    try:
        output_file = workflow.run(PRD_PATH, REPORT_PATH)

        print(f"\nValidation report created at:\n{output_file}")

    except OllamaConnectionError:
        print(
            "\nCould not connect to Ollama.\n\n"
            "Make sure the server is running with:\n\n"
            "ollama serve"
        )


if __name__ == "__main__":
    main()
