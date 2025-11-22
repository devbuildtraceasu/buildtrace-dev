"""
Pub/Sub Publisher for BuildTrace job queue
Publishes tasks to OCR, Diff, and Summary queues
"""

from typing import Dict, Any
import json
import logging
from config import config

# Optional import - only needed if USE_PUBSUB is True
try:
    from google.cloud import pubsub_v1
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    pubsub_v1 = None

logger = logging.getLogger(__name__)

class PubSubPublisher:
    """Publishes tasks to Pub/Sub topics"""
    
    def __init__(self, project_id: str = None):
        if not PUBSUB_AVAILABLE:
            raise ImportError("google-cloud-pubsub is not installed. Install it with: pip install google-cloud-pubsub")
        self.project_id = project_id or config.GCP_PROJECT_ID
        self.publisher = pubsub_v1.PublisherClient()
    
    def publish_ocr_task(self, job_id: str, drawing_version_id: str, metadata: Dict[str, Any]) -> str:
        """Publish OCR task to queue"""
        topic_path = self.publisher.topic_path(
            self.project_id, 
            config.PUBSUB_OCR_TOPIC
        )
        
        message_data = {
            'job_id': job_id,
            'stage': 'ocr',
            'drawing_version_id': drawing_version_id,
            'metadata': metadata
        }
        
        future = self.publisher.publish(
            topic_path,
            json.dumps(message_data).encode('utf-8'),
            job_id=job_id,
            stage='ocr'
        )
        
        message_id = future.result()
        logger.info(f"Published OCR task {job_id} as message {message_id}")
        return message_id
    
    def publish_diff_task(self, job_id: str, old_version_id: str, new_version_id: str, metadata: Dict[str, Any]) -> str:
        """Publish diff task to queue"""
        topic_path = self.publisher.topic_path(
            self.project_id,
            config.PUBSUB_DIFF_TOPIC
        )
        
        message_data = {
            'job_id': job_id,
            'stage': 'diff',
            'old_drawing_version_id': old_version_id,
            'new_drawing_version_id': new_version_id,
            'metadata': metadata
        }
        
        future = self.publisher.publish(
            topic_path,
            json.dumps(message_data).encode('utf-8'),
            job_id=job_id,
            stage='diff'
        )
        
        message_id = future.result()
        logger.info(f"Published Diff task {job_id} as message {message_id}")
        return message_id
    
    def publish_summary_task(self, job_id: str, diff_result_id: str, overlay_ref: str = None, metadata: Dict[str, Any] = None) -> str:
        """Publish summary task to queue"""
        topic_path = self.publisher.topic_path(
            self.project_id,
            config.PUBSUB_SUMMARY_TOPIC
        )
        
        message_data = {
            'job_id': job_id,
            'stage': 'summary',
            'diff_result_id': diff_result_id,
            'overlay_ref': overlay_ref,
            'metadata': metadata or {}
        }
        
        future = self.publisher.publish(
            topic_path,
            json.dumps(message_data).encode('utf-8'),
            job_id=job_id,
            stage='summary'
        )
        
        message_id = future.result()
        logger.info(f"Published Summary task {job_id} as message {message_id}")
        return message_id

