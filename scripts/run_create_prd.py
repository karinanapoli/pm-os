from pm_os.bootstrap import create_prd_workflow


def main():
    workflow = create_prd_workflow()

    output_path = workflow.run(
        output_path="features/03-prds/PRD.md",
    )

    print(f"PRD created at: {output_path}")


if __name__ == "__main__":
    main()