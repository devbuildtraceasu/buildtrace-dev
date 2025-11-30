# Logging Configuration

## Overview

BuildTrace uses Python's `logging` module with both console and file output for local development.

## Local Development

When running locally (`ENVIRONMENT=development`), logs are saved to the `logs/` directory:

### Log Files

1. **`logs/app.log`** - All application logs (DEBUG level and above)
   - Contains all log messages from the application
   - Rotates when file reaches 10MB
   - Keeps 5 backup files (app.log.1, app.log.2, etc.)

2. **`logs/errors.log`** - Error logs only (ERROR level and above)
   - Contains only errors and critical messages
   - Easier to find issues
   - Rotates when file reaches 10MB
   - Keeps 5 backup files

### Console Output

All logs are also printed to the console (stdout) for immediate feedback during development.

## Production

In production (`ENVIRONMENT=production`), logs are only sent to stdout/stderr, which is captured by:
- **Cloud Run**: Automatically captures stdout/stderr logs
- **Gunicorn**: Logs to stdout/stderr (configured in `entrypoint.py`)

No file logging is used in production to avoid disk space issues.

## Log Format

All logs use a consistent format:
```
YYYY-MM-DD HH:MM:SS.mmm [LEVEL] module:line - message
```

Example:
```
2025-11-24 15:30:45.123 [INFO] app:186 - Starting BuildTrace API in development mode
2025-11-24 15:30:45.124 [DEBUG] processing.ocr_pipeline:64 - Starting OCR pipeline
2025-11-24 15:30:45.125 [ERROR] processing.ocr_pipeline:474 - Error extracting page information: ...
```

## Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARNING**: Warning messages (non-critical issues)
- **ERROR**: Error messages (exceptions, failures)
- **CRITICAL**: Critical errors (system failures)

## Configuration

Logging is configured in `app.py`:

```python
# Console handler (always enabled)
console_handler = logging.StreamHandler(sys.stdout)

# File handlers (only in development)
if config.IS_DEVELOPMENT:
    # Application log
    file_handler = RotatingFileHandler('logs/app.log', ...)
    
    # Error log
    error_handler = RotatingFileHandler('logs/errors.log', ...)
```

## Viewing Logs

### Local Development

**View all logs:**
```bash
tail -f logs/app.log
```

**View only errors:**
```bash
tail -f logs/errors.log
```

**Search logs:**
```bash
grep "ERROR" logs/app.log
grep "OCR pipeline" logs/app.log
```

### Production (Cloud Run)

View logs in Google Cloud Console:
1. Go to Cloud Run service
2. Click on "Logs" tab
3. Filter by severity, time, or search terms

Or use `gcloud`:
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

## Log Rotation

Log files automatically rotate when they reach 10MB:
- Current file: `app.log`
- Backups: `app.log.1`, `app.log.2`, ..., `app.log.5`
- Oldest backup is deleted when rotation occurs

This prevents log files from growing indefinitely.

## Best Practices

1. **Use appropriate log levels:**
   - DEBUG: Detailed debugging info
   - INFO: Important events (startup, completion)
   - WARNING: Non-critical issues
   - ERROR: Exceptions and failures

2. **Include context:**
   ```python
   logger.info(f"Processing drawing {drawing_id}", extra={"drawing_id": drawing_id})
   ```

3. **Use structured logging for production:**
   - Include relevant IDs, timestamps, and context
   - Makes searching and filtering easier

4. **Don't log sensitive information:**
   - Never log API keys, passwords, or tokens
   - Be careful with user data

## Troubleshooting

### Logs not appearing in files

1. Check that `ENVIRONMENT=development` is set
2. Verify `logs/` directory exists and is writable
3. Check file permissions: `chmod 755 logs/`

### Log files too large

- Logs automatically rotate at 10MB
- Old backups are deleted (keeps 5 backups)
- You can manually delete old log files if needed

### Missing logs in production

- Production logs go to stdout/stderr only
- Check Cloud Run logs in Google Cloud Console
- Verify gunicorn is configured correctly

---

**Last Updated:** 2025-11-24

