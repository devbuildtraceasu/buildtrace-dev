"""
Pub/Sub Subscriber for BuildTrace workers
Subscribes to OCR, Diff, and Summary queues
"""

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.types import FlowControl
from typing import Callable
import json
import logging
import threading
import os

logger = logging.getLogger(__name__)

class PubSubSubscriber:
    """Subscribes to Pub/Sub topics and processes messages"""
    
    def __init__(self, project_id: str, subscription_name: str):
        self.project_id = project_id
        self.subscription_name = subscription_name
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(
            project_id, 
            subscription_name
        )
        self.running = False
        self.streaming_pull_future = None
    
    def start(self, callback: Callable):
        """Start listening for messages"""
        self.running = True
        
        def callback_wrapper(message):
            try:
                data = json.loads(message.data.decode('utf-8'))
                logger.info(f"Received message: {data.get('job_id', 'unknown')} on {self.subscription_name}")
                callback(data)
                message.ack()
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                message.nack()  # Retry later
        
        # Limit concurrent message processing to prevent OOM
        # Default to 1 for diff workers (memory intensive), 3 for others
        max_messages = int(os.getenv('PUBSUB_MAX_MESSAGES', '1'))
        flow_control = FlowControl(max_messages=max_messages)
        
        self.streaming_pull_future = self.subscriber.subscribe(
            self.subscription_path,
            callback=callback_wrapper,
            flow_control=flow_control
        )
        
        logger.info(f"Started listening on {self.subscription_name}")
        
        try:
            self.streaming_pull_future.result()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop listening"""
        self.running = False
        if self.streaming_pull_future:
            self.streaming_pull_future.cancel()
            logger.info(f"Stopped listening on {self.subscription_name}")

