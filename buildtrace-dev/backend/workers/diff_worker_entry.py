#!/usr/bin/env python3
"""Entry point for Diff worker service running in Cloud Run."""
import logging
import sys
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

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


class HealthHandler(BaseHTTPRequestHandler):
    """Simple health check handler for Cloud Run."""
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Diff Worker OK')
    
    def log_message(self, format, *args):
        # Suppress HTTP request logs
        pass


def run_health_server(port):
    """Run HTTP health check server."""
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"Health check server listening on port {port}")
    server.serve_forever()


def main():
    if not config.USE_PUBSUB:
        logger.error("USE_PUBSUB must be True for worker deployment")
        sys.exit(1)
    
    # Start health check server in background thread (Cloud Run requirement)
    port = int(os.getenv('PORT', '8080'))
    health_thread = threading.Thread(target=run_health_server, args=(port,), daemon=True)
    health_thread.start()
    
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

