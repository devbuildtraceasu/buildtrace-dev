"""
Cloud Tasks based asynchronous processing for BuildTrace
Replaces threading-based approach for Cloud Run compatibility
"""

import os
import json
import logging
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TaskProcessor:
    """Manages asynchronous processing using Cloud Tasks"""

    def __init__(self):
        self.client = tasks_v2.CloudTasksClient()
        self.project = os.getenv('GCP_PROJECT', 'buildtrace')
        self.location = os.getenv('GCP_REGION', 'us-central1')
        self.queue = os.getenv('TASK_QUEUE', 'drawing-processing')
        self.service_url = os.getenv('SERVICE_URL', 'https://buildtrace-overlay.run.app')

    def create_processing_task(self, session_id, old_path, new_path, old_name, new_name):
        """Create a Cloud Task for asynchronous drawing processing"""

        try:
            # Construct the queue path
            parent = self.client.queue_path(self.project, self.location, self.queue)

            # Create the task
            task = {
                'http_request': {
                    'http_method': tasks_v2.HttpMethod.POST,
                    'url': f'{self.service_url}/api/process-task',
                    'headers': {
                        'Content-Type': 'application/json',
                        # Add service account authorization if needed
                        'Authorization': f'Bearer {self._get_service_token()}'
                    },
                    'body': json.dumps({
                        'session_id': session_id,
                        'old_path': old_path,
                        'new_path': new_path,
                        'old_name': old_name,
                        'new_name': new_name,
                        'timestamp': datetime.utcnow().isoformat()
                    }).encode('utf-8')
                }
            }

            # Set task timeout (max 30 minutes for Cloud Tasks)
            task['dispatch_deadline'] = '1800s'

            # Set retry configuration
            task['retry_config'] = {
                'max_attempts': 3,
                'max_retry_duration': '3600s',
                'min_backoff': '10s',
                'max_backoff': '300s'
            }

            # Create the task
            response = self.client.create_task(parent=parent, task=task)

            logger.info(f"Created task for session {session_id}: {response.name}")
            return response.name

        except Exception as e:
            logger.error(f"Failed to create task for session {session_id}: {e}")
            raise

    def create_retry_task(self, session_id, delay_seconds=60):
        """Create a delayed retry task for failed processing"""

        try:
            parent = self.client.queue_path(self.project, self.location, self.queue)

            # Calculate schedule time
            schedule_time = timestamp_pb2.Timestamp()
            schedule_time.FromDatetime(datetime.utcnow() + timedelta(seconds=delay_seconds))

            task = {
                'http_request': {
                    'http_method': tasks_v2.HttpMethod.POST,
                    'url': f'{self.service_url}/api/retry-task',
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'session_id': session_id,
                        'retry_attempt': 1
                    }).encode('utf-8')
                },
                'schedule_time': schedule_time
            }

            response = self.client.create_task(parent=parent, task=task)
            logger.info(f"Created retry task for session {session_id}")
            return response.name

        except Exception as e:
            logger.error(f"Failed to create retry task: {e}")
            raise

    def _get_service_token(self):
        """Get service account token for authenticated requests"""
        try:
            import google.auth
            import google.auth.transport.requests

            credentials, project = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            return credentials.token
        except:
            return ""

    def list_pending_tasks(self):
        """List all pending tasks in the queue"""
        try:
            parent = self.client.queue_path(self.project, self.location, self.queue)

            tasks = []
            for task in self.client.list_tasks(parent=parent):
                tasks.append({
                    'name': task.name,
                    'create_time': task.create_time,
                    'schedule_time': task.schedule_time,
                    'dispatch_count': task.dispatch_count,
                    'response_count': task.response_count
                })

            return tasks

        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []

    def cancel_task(self, task_name):
        """Cancel a specific task"""
        try:
            self.client.delete_task(name=task_name)
            logger.info(f"Cancelled task: {task_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel task: {e}")
            return False


# Global instance
task_processor = TaskProcessor()