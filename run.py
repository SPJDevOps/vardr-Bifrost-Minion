#!/usr/bin/env python3
"""
Run script for the Download Minion application using FastStream
"""
import asyncio
from app.main import app

if __name__ == "__main__":
    asyncio.run(app.run()) 