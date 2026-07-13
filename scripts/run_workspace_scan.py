from pm_os.bootstrap import create_workspace_scan_workflow


def main() -> None:
    workflow = create_workspace_scan_workflow()
    report = workflow.run()
    print(report)


if __name__ == "__main__":
    main()
