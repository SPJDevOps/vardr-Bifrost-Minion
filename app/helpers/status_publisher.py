import json
from aio_pika import Message

from app.models.hyperloop_download import HyperloopDownload

async def publish_status_update(rabbitmq, queue_name, download: HyperloopDownload):
    """
    Publishes the status update of the download object to the specified queue.
    
    :param rabbitmq: RabbitMQ connection object
    :param queue_name: The name of the queue to publish to
    :param download: The HyperloopDownload object containing the current status
    """
    message_body = json.dumps(download.to_dict())
    
    # Publish the message to the queue
    await rabbitmq.channel.default_exchange.publish(
        Message(body=message_body.encode()),  # Convert string to bytes
        routing_key=queue_name
    )
    
    print(f"Published to {queue_name} with status: {download.status}")