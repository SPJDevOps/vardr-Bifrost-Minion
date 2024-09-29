# app/main.py
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.rabbitmq.rabbitmq import RabbitMQ
from app.rabbitmq.rabbit_consumer import Consumer
from app.rabbitmq.rabbit_publisher import Publisher

app = FastAPI()
rabbitmq = RabbitMQ("amqp://guest:guest@localhost:5672/")  # Adjust the URL as needed
consumer = Consumer(rabbitmq, 'private.hyperloop.download_requests', 'private.hyperloop.download_status')
publisher = Publisher(rabbitmq)

# Define an async context manager for handling startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    await rabbitmq.connect()
    asyncio.create_task(consumer.start_consuming())
    yield
    # Shutdown event
    await rabbitmq.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/publish")
async def publish_message(message: str):
    await publisher.publish_message('first_queue', message)
    return {"status": "Message published"}