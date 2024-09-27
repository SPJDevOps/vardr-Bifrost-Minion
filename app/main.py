# app/main.py
import asyncio
from fastapi import FastAPI
from app.rabbitmq.rabbitmq import RabbitMQ
from app.rabbitmq.rabbit_consumer import Consumer
from app.rabbitmq.rabbit_publisher import Publisher

app = FastAPI()
rabbitmq = RabbitMQ("amqp://guest:guest@localhost:5672/")  # Adjust the URL as needed
consumer = Consumer(rabbitmq, 'private.hyperloop.download_requests', 'private.hyperloop.download_status')
publisher = Publisher(rabbitmq)

@app.on_event("startup")
async def startup_event():
    await rabbitmq.connect()
    # Start the consumer in the background
    asyncio.create_task(consumer.start_consuming())

@app.on_event("shutdown")
async def shutdown_event():
    await rabbitmq.close()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/publish")
async def publish_message(message: str):
    await publisher.publish_message('first_queue', message)
    return {"status": "Message published"}