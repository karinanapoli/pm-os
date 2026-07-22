#!/usr/bin/env python3
"""
PM Studio Web Interface.

Usage:
    python scripts/run_web.py

Then open http://localhost:8000 in your browser.
"""

import os
import sys

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import uvicorn

if __name__ == "__main__":
    host = os.getenv("PM_OS_HOST", "127.0.0.1")
    port = int(os.getenv("PM_OS_PORT", "8000"))
    url = f"http://{host}:{port}"
    if host == "0.0.0.0":
        url = f"http://localhost:{port}"
    print(f"🚀 PM Studio — {url}")
    reload_flag = os.getenv("PM_OS_RELOAD", "1") == "1"
    uvicorn.run("pm_os.web.app:app", host=host, port=port, reload=reload_flag)
