import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "pm_os.web.app:app",
        host=os.getenv("PM_OS_HOST", "127.0.0.1"),
        port=int(os.getenv("PM_OS_PORT", "8000")),
    )
