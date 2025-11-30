# BuildTrace Development Guide

Development workflow, coding standards, testing practices, and contribution guidelines.

## Table of Contents

1. [Development Workflow](#development-workflow)
2. [Code Style](#code-style)
3. [Git Workflow](#git-workflow)
4. [Testing](#testing)
5. [Debugging](#debugging)
6. [Code Review](#code-review)

## Development Workflow

### Local Development Setup

1. **Clone Repository:**
```bash
git clone <repository-url>
cd buildtrace-overlay
```

2. **Create Virtual Environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

3. **Install Dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists
```

4. **Configure Environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Initialize Database** (if using):
```bash
python -c "from gcp.database import init_db; init_db()"
```

6. **Run Application:**
```bash
python app.py
```

### Development Server

**Flask Development Server:**
```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --port=5001
```

**With Auto-Reload:**
```bash
flask run --reload --port=5001
```

### Hot Reload

The Flask development server automatically reloads on code changes. For other processes:

```bash
# Use watchdog for file watching
pip install watchdog
watchmedo auto-restart --patterns="*.py" --recursive -- python app.py
```

## Code Style

### Python Style Guide

Follow **PEP 8** with these modifications:

**Line Length:** 100 characters (not 79)

**Imports:** Grouped and sorted
```python
# Standard library
import os
import sys
from datetime import datetime

# Third-party
import cv2
import numpy as np
from flask import Flask, request

# Local
from config import config
from gcp.database import get_db_session
```

**Naming Conventions:**
- **Classes**: `PascalCase` (e.g., `CloudStorageService`)
- **Functions/Variables**: `snake_case` (e.g., `get_db_session`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_UPLOAD_SIZE`)
- **Private**: Prefix with `_` (e.g., `_internal_method`)

### Code Formatting

**Use Black** (when configured):
```bash
black --line-length 100 .
```

**Use isort** for imports:
```bash
isort .
```

### Type Hints

Use type hints for function signatures:

```python
from typing import Optional, List, Dict

def process_drawing(
    file_path: str,
    dpi: int = 300,
    debug: bool = False
) -> Dict[str, any]:
    """Process a drawing file.
    
    Args:
        file_path: Path to drawing file
        dpi: Resolution for conversion
        debug: Enable debug mode
        
    Returns:
        Dictionary with processing results
    """
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def align_drawings(old_img: np.ndarray, new_img: np.ndarray) -> np.ndarray:
    """Align two drawing images using SIFT feature matching.
    
    This function detects features in both images, matches them, and
    applies an affine transformation to align the old image with the new.
    
    Args:
        old_img: Old drawing image as numpy array
        new_img: New drawing image as numpy array
        
    Returns:
        Aligned old image as numpy array
        
    Raises:
        ValueError: If insufficient features are detected
        RuntimeError: If alignment fails
    """
    pass
```

## Git Workflow

### Branch Strategy

- **main**: Production-ready code
- **develop**: Integration branch
- **feature/**: Feature branches
- **bugfix/**: Bug fix branches
- **hotfix/**: Urgent production fixes

### Commit Messages

Follow **Conventional Commits**:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

**Examples:**
```
feat(api): Add session summary endpoint

Add new endpoint to get aggregated summary of all drawings
in a session with statistics and recommendations.

Closes #123
```

```
fix(pipeline): Fix alignment score calculation

Correct alignment score calculation to use normalized
feature match ratio instead of raw match count.

Fixes #456
```

### Pull Request Process

1. **Create Feature Branch:**
```bash
git checkout -b feature/new-endpoint
```

2. **Make Changes:**
```bash
# Make code changes
git add .
git commit -m "feat(api): Add new endpoint"
```

3. **Push and Create PR:**
```bash
git push origin feature/new-endpoint
# Create PR on GitHub
```

4. **Code Review:**
- Address review comments
- Update PR description
- Ensure tests pass

5. **Merge:**
- Squash and merge (preferred)
- Delete branch after merge

## Testing

### Test Structure

```
tests/
├── __init__.py
├── conftest.py
├── test_api.py
├── test_pipeline.py
├── test_alignment.py
└── test_database.py
```

### Unit Tests

**Example:**
```python
import pytest
from align_drawings import align_drawings
import cv2
import numpy as np

def test_align_drawings_success():
    """Test successful alignment of two images."""
    old_img = cv2.imread('tests/fixtures/old.png')
    new_img = cv2.imread('tests/fixtures/new.png')
    
    aligned = align_drawings(old_img, new_img)
    
    assert aligned is not None
    assert aligned.shape == new_img.shape
```

### Integration Tests

**Example:**
```python
def test_complete_pipeline(client):
    """Test complete processing pipeline."""
    response = client.post('/upload', data={
        'old_file': open('tests/fixtures/old.pdf', 'rb'),
        'new_file': open('tests/fixtures/new.pdf', 'rb')
    })
    
    assert response.status_code == 200
    session_id = response.json['session_id']
    
    # Process
    response = client.post(f'/process/{session_id}')
    assert response.status_code == 200
    
    # Check results
    response = client.get(f'/results/{session_id}')
    assert response.status_code == 200
    assert 'changes' in response.json
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_api.py::test_upload_endpoint
```

### Test Fixtures

**conftest.py:**
```python
import pytest
from app import app
from gcp.database import get_db_session

@pytest.fixture
def client():
    """Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def db_session():
    """Database session for testing."""
    with get_db_session() as db:
        yield db
        db.rollback()
```

## Debugging

### Debug Mode

Enable debug mode for detailed error messages:

```python
# In app.py
app.config['DEBUG'] = True
```

### Logging

Use structured logging:

```python
import logging

logger = logging.getLogger(__name__)

def process_file(file_path: str):
    logger.info(f"Processing file: {file_path}")
    try:
        # Process
        logger.debug(f"File processed successfully")
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        raise
```

### Debugger

Use Python debugger:

```python
import pdb

def problematic_function():
    # Set breakpoint
    pdb.set_trace()
    # Code execution pauses here
    pass
```

Or use IDE debugger (VS Code, PyCharm).

### Print Debugging

For quick debugging:

```python
print(f"DEBUG: Variable value: {variable}")
print(f"DEBUG: Function called with: {args}")
```

**Note**: Remove debug prints before committing.

## Code Review

### Review Checklist

**Functionality:**
- [ ] Code works as intended
- [ ] Handles edge cases
- [ ] Error handling is appropriate
- [ ] Performance is acceptable

**Code Quality:**
- [ ] Follows style guide
- [ ] Has appropriate comments
- [ ] No hardcoded values
- [ ] Uses configuration properly

**Testing:**
- [ ] Tests added/updated
- [ ] Tests pass
- [ ] Coverage maintained

**Documentation:**
- [ ] Docstrings added
- [ ] README updated if needed
- [ ] API docs updated

### Review Comments

**Be Constructive:**
- Explain why, not just what
- Suggest alternatives
- Acknowledge good work

**Example:**
```
Good: "Consider using a dictionary here instead of multiple if/else 
       statements for better readability and maintainability."

Bad: "This is wrong."
```

## Best Practices

### Error Handling

```python
# Good
try:
    result = process_file(file_path)
except FileNotFoundError:
    logger.error(f"File not found: {file_path}")
    raise
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
    return {"error": str(e)}, 500
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

### Resource Management

```python
# Use context managers
with open(file_path, 'r') as f:
    content = f.read()

with get_db_session() as db:
    session = db.query(Session).filter_by(id=session_id).first()
```

### Configuration

```python
# Use config, not hardcoded values
from config import config

if config.USE_DATABASE:
    # Use database
    pass
```

### Security

- Never commit secrets
- Validate all inputs
- Use parameterized queries
- Sanitize file paths
- Check file types and sizes

### Performance

- Use connection pooling
- Cache expensive operations
- Process in chunks for large files
- Use async processing when appropriate
- Monitor memory usage

## IDE Setup

### VS Code

**Recommended Extensions:**
- Python
- Pylance
- Black Formatter
- isort
- Python Test Explorer

**.vscode/settings.json:**
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "editor.formatOnSave": true
}
```

### PyCharm

**Settings:**
- Code Style: PEP 8
- Formatter: Black
- Type Checking: Enable

## Documentation

### Code Comments

```python
# Good: Explains why
# Use SIFT because it's robust to scale and rotation changes
# common in architectural drawings
sift = cv2.SIFT_create()

# Bad: States the obvious
# Create SIFT object
sift = cv2.SIFT_create()
```

### Update Documentation

When making changes:
- Update relevant documentation
- Add examples if needed
- Update API docs
- Update README if behavior changes

---

**Next Steps**: See [ROADMAP.md](./ROADMAP.md) for planned features or [API.md](./API.md) for API usage.

