from pm_os.bootstrap import create_prd_workflow


def main() -> None:
    workflow = create_prd_workflow()

    workflow.run(
        "workspace/initiatives/INT-0001-consulta-inteligente-fornecedores/artifacts/prd.md"
    )


if __name__ == "__main__":
    main()