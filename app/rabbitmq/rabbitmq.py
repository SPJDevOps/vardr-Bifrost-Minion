# app/rabbitmq.py
import asyncio
from aio_pika import connect_robust, IncomingMessage, Message, ExchangeType

class RabbitMQ:
    def __init__(self, amqp_url):
        self.amqp_url = amqp_url
        self.connection = None
        self.channel = None

    async def connect(self):
        self.connection = await connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        print("Connected to RabbitMQ")

    async def close(self):
        await self.connection.close()