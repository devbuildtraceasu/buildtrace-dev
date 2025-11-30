"""
Pub/Sub module for BuildTrace async job processing

Contains:
- publisher.py: Pub/Sub publisher for enqueueing tasks
- subscriber.py: Pub/Sub subscriber for worker services
"""

# Optional imports - only available if google-cloud-pubsub is installed
try:
    from .publisher import PubSubPublisher
    from .subscriber import PubSubSubscriber
    __all__ = ['PubSubPublisher', 'PubSubSubscriber']
except ImportError as e:
    logger = __import__('logging').getLogger(__name__)
    logger.warning(f"Pub/Sub not available: {e}")
    PubSubPublisher = None
    PubSubSubscriber = None
    __all__ = []

