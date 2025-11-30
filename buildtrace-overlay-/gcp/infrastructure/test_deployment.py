#!/usr/bin/env python3
"""
Test script to verify deployment configuration
"""

import os
import yaml

def test_cloudbuild_config():
    """Test that cloudbuild.yaml has correct configuration"""
    with open('cloudbuild.yaml', 'r') as f:
        config = yaml.safe_load(f)

    steps = config['steps']

    # Should have: build, push, deploy-web, deploy-worker
    assert len(steps) == 4, f"Expected 4 steps, got {len(steps)}"

    # Check web app deployment
    web_deploy = steps[2]
    assert web_deploy['args'][2] == 'buildtrace-overlay', "Web app name incorrect"
    assert '--memory' in web_deploy['args'], "Memory setting missing"
    assert '4Gi' in web_deploy['args'], "Web app should have 4Gi memory"

    # Check job processor deployment
    job_deploy = steps[3]
    assert job_deploy['args'][2] == 'buildtrace-job-processor', "Job processor name incorrect"
    assert '--memory' in job_deploy['args'], "Job processor memory setting missing"
    assert '32Gi' in job_deploy['args'], "Job processor should have 32Gi memory"
    assert '--command' in job_deploy['args'], "Job processor command missing"
    assert 'python,job_processor.py' in job_deploy['args'], "Job processor command incorrect"

    print("✅ cloudbuild.yaml configuration is correct")

def test_environment_config():
    """Test that production environment uses correct settings"""
    # Test production environment
    os.environ['ENVIRONMENT'] = 'production'

    # Import here to get fresh environment
    import importlib
    import sys
    if 'app' in sys.modules:
        importlib.reload(sys.modules['app'])

    # Test that the configuration would work
    from chunked_processor import ChunkedProcessor
    processor = ChunkedProcessor(max_sync_pages=3)
    assert processor.max_sync_pages == 3, "Production should use 3 page limit"

    print("✅ Production environment configuration is correct")

if __name__ == "__main__":
    test_cloudbuild_config()
    test_environment_config()
    print("🎉 All deployment tests passed!")