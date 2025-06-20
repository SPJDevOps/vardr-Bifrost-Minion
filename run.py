#!/usr/bin/env python3
"""
Run script for the Download Minion application using FastStream
"""
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        "app.main:fastapi_app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 