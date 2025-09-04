# app/main.py
import os
from faststream import FastStream
from app.processors.download_router import broker

# Create FastStream app using the broker from download_router
app = FastStream(broker)