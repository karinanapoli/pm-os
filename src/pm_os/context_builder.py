from pm_os.domain.initiative import Initiative


class ContextBuilder:
    """
    Builds the context used by PM OS workflows.
    """

    def build(self, initiative: Initiative) -> str:
        """
        Builds a single context string from all initiative documents.
        """

        return "\n\n".join(initiative.documents)