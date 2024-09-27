# app/consumer.py
import asyncio
import json
from aio_pika import IncomingMessage

from app.models.hyperloop_download import HyperloopDownload
from app.processors.docker_processor import DockerProcessor
from app.processors.maven_processor import MavenProcessor

class Consumer:
    def __init__(self, rabbitmq, request_queue, status_queue):
        self.rabbitmq = rabbitmq
        self.request_queue = request_queue
        self.status_queue = status_queue
        self.docker_processor = DockerProcessor(rabbitmq, status_queue)
        self.maven_processor = MavenProcessor(rabbitmq, status_queue)

    async def handle_message(self, message: IncomingMessage):
        async with message.process():
            body = message.body.decode()
            data = json.loads(body)
            
            download = HyperloopDownload.from_dict(data)
            print(f"Received download: {download}")
            
            if download.type == "DOCKER":
                await self.docker_processor.process(download)
            elif download.type == "MAVEN":
                await self.maven_processor.process(download)
            else:
                print(f"Unknown download type: {download.type}")

    async def start_consuming(self):
        queue = await self.rabbitmq.channel.declare_queue(self.request_queue, durable=True)
        await queue.consume(self.handle_message)
        print(f"Started consuming from {self.request_queue}")