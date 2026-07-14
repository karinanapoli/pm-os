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
    print("🚀 PM Studio — http://localhost:8000")
    uvicorn.run("pm_os.web.app:app", host="0.0.0.0", port=8000, reload=True)
