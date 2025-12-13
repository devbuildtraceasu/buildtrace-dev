#!/usr/bin/env python3
"""
HTTP wrapper for OCR Worker - receives Pub/Sub push messages.
Deployed as a Cloud Run service that receives HTTP POST from Pub/Sub.
"""
import os
import sys
import json
import base64
import logging
from flask import Flask, request, jsonify

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import config
from workers.ocr_worker import OCRWorker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
worker = None

def get_worker():
    global worker
    if worker is None:
        worker = OCRWorker()
    return worker

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'ocr-worker'}), 200

@app.route('/', methods=['POST'])
def handle_pubsub_push():
    """
    Handle Pub/Sub push messages.
    Pub/Sub sends messages as JSON with base64-encoded data.
    """
    try:
        envelope = request.get_json()
        if not envelope:
            logger.error("No Pub/Sub message received")
            return jsonify({'error': 'No message'}), 400
        
        if 'message' not in envelope:
            logger.error("Invalid Pub/Sub message format")
            return jsonify({'error': 'Invalid format'}), 400
        
        pubsub_message = envelope['message']
        
        # Decode the base64-encoded data
        if 'data' in pubsub_message:
            data = base64.b64decode(pubsub_message['data']).decode('utf-8')
            message = json.loads(data)
        else:
            message = {}
        
        # Add any attributes
        if 'attributes' in pubsub_message:
            message.update(pubsub_message['attributes'])
        
        logger.info(f"Received OCR task: job_id={message.get('job_id')}, version_id={message.get('drawing_version_id')}")
        
        # Process the message
        ocr_worker = get_worker()
        ocr_worker.process_message(message)
        
        logger.info(f"OCR task completed: job_id={message.get('job_id')}")
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.exception(f"Error processing OCR task: {e}")
        # Return 500 so Pub/Sub will retry
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting OCR Worker HTTP server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

