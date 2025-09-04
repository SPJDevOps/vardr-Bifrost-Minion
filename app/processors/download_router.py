"""
Download router using FastStream for handling download requests.
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any

from faststream import Logger, ContextRepo
from faststream.rabbit import RabbitBroker, RabbitQueue, RabbitMessage

from app.models.hyperloop_download import HyperloopDownload
from app.models.exceptions import UserInputError, DependencyNotFoundError, InternalError
from app.processors.docker_processor import DockerProcessor
from app.processors.maven_processor import MavenProcessor
from app.processors.python_package_processor import PythonPackageProcessor
from app.processors.file_download_processor import FileDownloadProcessor
from app.processors.npm_package_processor import NpmPackageProcessor
from app.processors.helm_chart_processor import HelmChartProcessor
from app.processors.website_pdf_processor import WebsitePdfProcessor

# Create broker instance with RabbitMQ connection
broker = RabbitBroker(
    url=os.getenv("RABBITMQ_HOST", "amqp://guest:guest@localhost:5672/")
)

# Create queues
download_request_queue = RabbitQueue(
    name=os.getenv("RABBITMQ_DOWNLOAD_REQUEST_QUEUE", "private.hyperloop.download_requests"),
    durable=True
)

download_status_queue = RabbitQueue(
    name=os.getenv("RABBITMQ_DOWNLOAD_STATUS_QUEUE", "private.hyperloop.download_status"),
    durable=True
)

# Initialize processors
docker_processor = DockerProcessor(broker, download_status_queue.name)
maven_processor = MavenProcessor(broker, download_status_queue.name)
python_package_processor = PythonPackageProcessor(broker, download_status_queue.name)
npm_package_processor = NpmPackageProcessor(broker, download_status_queue.name)
file_download_processor = FileDownloadProcessor(broker, download_status_queue.name)
helm_chart_processor = HelmChartProcessor(broker, download_status_queue.name)
website_pdf_processor = WebsitePdfProcessor(broker, download_status_queue.name)

@broker.subscriber(download_request_queue)
async def handle_download_request(
    message: str,
    logger: Logger,
    context: ContextRepo,
    raw_message: RabbitMessage
):
    """Handle download requests from the queue with proper error handling"""
    try:
        # Parse the message
        if isinstance(message, str):
            data = json.loads(message)
        else:
            data = message
            
        download = HyperloopDownload.from_dict(data)
        logger.info(f"Processing download request: {download}")
        
        # Validate download type
        valid_types = ["DOCKER", "MAVEN", "PYTHON", "NPM", "FILE", "HELM", "WEBSITE"]
        if download.type not in valid_types:
            raise UserInputError(f"Invalid download type: {download.type}. Valid types: {valid_types}")
        
        # Route to appropriate processor based on type
        if download.type == "DOCKER":
            await docker_processor.process(download)
        elif download.type == "MAVEN":
            await maven_processor.process(download)
        elif download.type == "PYTHON":
            await python_package_processor.process(download)
        elif download.type == "NPM":
            await npm_package_processor.process(download)
        elif download.type == "FILE":
            await file_download_processor.process(download)
        elif download.type == "HELM":
            await helm_chart_processor.process(download)
        elif download.type == "WEBSITE":
            await website_pdf_processor.process(download)
            
    except (UserInputError, DependencyNotFoundError) as e:
        # Reject message - don't retry for user input errors
        logger.error(f"User input error - rejecting message: {str(e)}")
        await raw_message.reject(requeue=False)
        raise
        
    except InternalError as e:
        # Negative acknowledgment - message will be retried
        logger.error(f"Internal error - will retry: {str(e)}")
        await raw_message.nack(requeue=True)
        raise
        
    except Exception as e:
        # Unexpected error - treat as internal error and retry
        logger.error(f"Unexpected error - will retry: {str(e)}")
        await raw_message.nack(requeue=True)
        raise

async def publish_status_update(download: HyperloopDownload):
    """Publish status updates to the status queue"""
    await broker.publish(
        download.to_dict(),
        queue=download_status_queue
    )

# The broker itself acts as the router with the @broker.subscriber decorators above 