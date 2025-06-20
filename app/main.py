# app/main.py
import os
from fastapi import FastAPI
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitQueue
from app.processors.download_router import download_router

# Create FastStream app with RabbitMQ broker
broker = RabbitBroker(
    os.getenv("RABBITMQ_HOST", "amqp://guest:guest@localhost:5672/")
)

# Create FastStream app
app = FastStream(broker)

# Create FastAPI app
fastapi_app = FastAPI()

# Include the download router
app.include_router(download_router)

# Add FastAPI routes
@fastapi_app.get("/")
async def read_root():
    return {"Hello": "World"}

@fastapi_app.post("/publish")
async def publish_message(message: str):
    # Publish to the download request queue
    await broker.publish(
        message, 
        queue=os.getenv("RABBITMQ_DOWNLOAD_REQUEST_QUEUE", "private.hyperloop.download_requests")
    )
    return {"status": "Message published"}

# Mount FastAPI app to FastStream
app.mount_app(fastapi_app)