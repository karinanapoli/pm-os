from datetime import datetime


class ConsoleLogger:
    """
    Simple logger that writes messages to the console.
    """

    def info(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [INFO] {message}")