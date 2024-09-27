# app/publisher.py
from aio_pika import Message

class Publisher:
    def __init__(self, rabbitmq):
        self.rabbitmq = rabbitmq

    async def publish_message(self, routing_key, message_body):
        await self.rabbitmq.channel.default_exchange.publish(
            Message(body=message_body.encode()),
            routing_key=routing_key
        )
        print(f"Published message to {routing_key}")