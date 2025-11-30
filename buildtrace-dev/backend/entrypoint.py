#!/usr/bin/env python3
"""
Cloud Run entrypoint for BuildTrace backend
Ensures proper PORT handling and gunicorn startup
"""
import os
import sys

def main():
    # Get PORT from environment (Cloud Run sets this automatically)
    port = os.environ.get('PORT', '8080')
    
    # Gunicorn command
    cmd = [
        'gunicorn',
        '--bind', f'0.0.0.0:{port}',
        '--workers', '2',
        '--threads', '4',
        '--timeout', '3600',
        '--access-logfile', '-',
        '--error-logfile', '-',
        '--log-level', 'info',
        '--preload',
        'app:app'
    ]
    
    # Execute gunicorn (replaces current process)
    os.execvp('gunicorn', cmd)

if __name__ == '__main__':
    main()

