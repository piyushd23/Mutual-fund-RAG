#!/usr/bin/env python3
"""
SBI Mutual Fund FAQ Assistant — Server Launcher
Launches the FastAPI web application and REST API server.

Usage:
    python3 run.py
    # or with custom port:
    PORT=8080 python3 run.py
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

load_dotenv()

def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print("=" * 60)
    print(" 📊 Starting SBI Mutual Fund FAQ Assistant (FastAPI Server)")
    print(f" 🌐 Access Web UI at : http://localhost:{port}")
    print(f" 📄 API Docs at       : http://localhost:{port}/docs")
    print(f" ⚙️  Generator Mode   : {os.getenv('GENERATOR_MODE', 'local').upper()}")
    print("=" * 60)

    uvicorn.run(
        "ui.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )

if __name__ == "__main__":
    main()
