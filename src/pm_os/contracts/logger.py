from typing import Protocol


class Logger(Protocol):
    """
    Contract for application logging.

    Workflows depend on this abstraction, not on a concrete logger.
    """

    def info(self, message: str) -> None:
        ...