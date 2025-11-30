#!/usr/bin/env python3
"""Entry point for Diff worker service running in GKE."""
import logging
import sys
import os

# Add backend directory to path (when running from /app in container)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import config
from gcp.pubsub import PubSubSubscriber
from workers.diff_worker import DiffWorker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    if not config.USE_PUBSUB:
        logger.error("USE_PUBSUB must be True for worker deployment")
        sys.exit(1)
    
    logger.info(f"Starting Diff worker")
    logger.info(f"Project: {config.GCP_PROJECT_ID}")
    logger.info(f"Subscription: {config.PUBSUB_DIFF_SUBSCRIPTION}")
    
    try:
        subscriber = PubSubSubscriber(
            project_id=config.GCP_PROJECT_ID,
            subscription_name=config.PUBSUB_DIFF_SUBSCRIPTION
        )
        worker = DiffWorker()
        
        logger.info("Diff worker ready, listening for messages...")
        subscriber.start(worker.process_message)
    except KeyboardInterrupt:
        logger.info("Shutting down Diff worker...")
    except Exception as e:
        logger.exception(f"Fatal error in Diff worker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

