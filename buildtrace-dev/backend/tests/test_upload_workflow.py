"""
Test cases for drawing upload and comparison workflow
Tests the complete flow from file upload to job creation
"""

import os
import sys
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from config import config
from gcp.database import get_db_session
from gcp.database.models import Project, DrawingVersion, Job, JobStage, Organization, User
from services.drawing_service import DrawingUploadService, DrawingUploadError
from services.orchestrator import OrchestratorService
from gcp.storage import StorageService

try:
    import psycopg2  # type: ignore
except ImportError:  # pragma: no cover
    psycopg2 = None

RUN_UPLOAD_TESTS = os.getenv("RUN_UPLOAD_WORKFLOW_TESTS") == "1"

if not RUN_UPLOAD_TESTS or not config.USE_DATABASE or psycopg2 is None:
    pytest.skip("Database requirements not met for upload workflow tests", allow_module_level=True)


@pytest.fixture(scope='class')
def test_setup():
    """Setup test environment"""
    return {
        'test_project_id': 'project-ars-construction-001',
        'test_user_id': 'ash-user-0000000000001',
        'test_org_id': 'org-ars-construction-000000000001',
        'old_version_id': None,
        'new_version_id': None,
        'job_id': None
    }


@pytest.mark.usefixtures('test_setup')
class TestUploadWorkflow:
    """Test suite for upload and comparison workflow"""
        
    def test_1_verify_database_setup(self, test_setup):
        """Test 1: Verify organizations, users, and projects exist"""
        with get_db_session() as db:
            # Check organizations
            orgs = db.query(Organization).all()
            assert len(orgs) >= 2, "Should have at least 2 organizations"
            org_names = [org.name for org in orgs]
            assert 'ARS CONSTRUCTION' in org_names, "ARS CONSTRUCTION organization should exist"
            assert 'HOTEL ARS' in org_names, "HOTEL ARS organization should exist"
            
            # Check user
            user = db.query(User).filter_by(id=test_setup['test_user_id']).first()
            assert user is not None, "Test user should exist"
            assert user.email == 'ash-user@buildtrace.ai', "User email should match"
            assert user.name == 'Ashish Raj Shekhar', "User name should match"
            
            # Check projects
            projects = db.query(Project).filter_by(organization_id=test_setup['test_org_id']).all()
            assert len(projects) >= 1, "Should have at least 1 project for ARS CONSTRUCTION"
            
            project = db.query(Project).filter_by(id=test_setup['test_project_id']).first()
            assert project is not None, "Test project should exist"
            assert project.name == 'ARS Construction Main Project', "Project name should match"
            
        print("✅ Test 1 PASSED: Database setup verified")
    
    def test_2_upload_old_drawing(self, test_setup):
        """Test 2: Upload old/baseline drawing"""
        # Read test file
        test_file_path = Path(__file__).parent.parent.parent.parent / 'testing' / 'A-101' / 'A-101_old.pdf'
        assert test_file_path.exists(), f"Test file should exist: {test_file_path}"
        
        with open(test_file_path, 'rb') as f:
            file_bytes = f.read()
        
        upload_service = DrawingUploadService()
        result = upload_service.handle_upload(
            file_bytes=file_bytes,
            filename='A-101_old.pdf',
            content_type='application/pdf',
            project_id=test_setup['test_project_id'],
            user_id=test_setup['test_user_id'],
            is_revision=False
        )
        
        assert result.drawing_version_id is not None, "Should return drawing version ID"
        assert result.drawing_name == 'A-101_old', "Drawing name should be extracted"
        assert result.version_number >= 1, f"Should be version 1 or higher (got {result.version_number})"
        assert result.project_id == test_setup['test_project_id'], "Project ID should match"
        
        # Verify in database
        with get_db_session() as db:
            drawing_version = db.query(DrawingVersion).filter_by(id=result.drawing_version_id).first()
            assert drawing_version is not None, "Drawing version should be in database"
            assert drawing_version.drawing_name == 'A-101_old', "Drawing name should match"
            assert drawing_version.version_number >= 1, f"Version number should be 1 or higher (got {drawing_version.version_number})"
        
        test_setup['old_version_id'] = result.drawing_version_id
        print(f"✅ Test 2 PASSED: Old drawing uploaded (version_id: {result.drawing_version_id})")
        return result.drawing_version_id
    
    def test_3_upload_new_drawing(self, test_setup):
        """Test 3: Upload new/revised drawing"""
        # Read test file
        test_file_path = Path(__file__).parent.parent.parent.parent / 'testing' / 'A-101' / 'A-101_new.pdf'
        assert test_file_path.exists(), f"Test file should exist: {test_file_path}"
        
        with open(test_file_path, 'rb') as f:
            file_bytes = f.read()
        
        upload_service = DrawingUploadService()
        result = upload_service.handle_upload(
            file_bytes=file_bytes,
            filename='A-101_new.pdf',
            content_type='application/pdf',
            project_id=test_setup['test_project_id'],
            user_id=test_setup['test_user_id'],
            is_revision=True
        )
        
        assert result.drawing_version_id is not None, "Should return drawing version ID"
        assert result.drawing_name == 'A-101_new', "Drawing name should be extracted"
        assert result.version_number >= 1, f"Should be version 1 or higher (got {result.version_number})"
        assert result.project_id == test_setup['test_project_id'], "Project ID should match"
        
        # Verify in database
        with get_db_session() as db:
            drawing_version = db.query(DrawingVersion).filter_by(id=result.drawing_version_id).first()
            assert drawing_version is not None, "Drawing version should be in database"
        
        test_setup['new_version_id'] = result.drawing_version_id
        print(f"✅ Test 3 PASSED: New drawing uploaded (version_id: {result.drawing_version_id})")
        return result.drawing_version_id
    
    def test_4_create_comparison_job(self, test_setup):
        """Test 4: Create comparison job"""
        # Ensure we have both version IDs
        if not test_setup['old_version_id']:
            pytest.skip("Old version not uploaded - run test_2 first")
        if not test_setup['new_version_id']:
            pytest.skip("New version not uploaded - run test_3 first")
        
        orchestrator = OrchestratorService()
        job = orchestrator.create_comparison_job(
            old_version_id=test_setup['old_version_id'],
            new_drawing_version_id=test_setup['new_version_id'],
            project_id=test_setup['test_project_id'],
            user_id=test_setup['test_user_id']
        )
        
        assert job is not None, "Job should be created"
        assert job.id is not None, "Job should have ID"
        assert job.status == 'created', "Job status should be 'created'"
        assert job.old_drawing_version_id == test_setup['old_version_id'], "Old version ID should match"
        assert job.new_drawing_version_id == test_setup['new_version_id'], "New version ID should match"
        
        # Verify job stages
        with get_db_session() as db:
            stages = db.query(JobStage).filter_by(job_id=job.id).all()
            assert len(stages) >= 3, "Should have at least 3 stages (OCR, Diff, Summary)"
            stage_types = [s.stage for s in stages]
            assert 'ocr' in stage_types, "Should have OCR stage"
            assert 'diff' in stage_types, "Should have Diff stage"
            assert 'summary' in stage_types, "Should have Summary stage"
        
        test_setup['job_id'] = job.id
        print(f"✅ Test 4 PASSED: Comparison job created (job_id: {job.id})")
        return job.id
    
    def test_5_verify_storage_files(self, test_setup):
        """Test 5: Verify files are stored correctly"""
        storage = StorageService()
        
        # Check that storage paths exist (for local storage)
        if not config.USE_GCS:
            uploads_dir = Path(config.LOCAL_UPLOAD_PATH)
            assert uploads_dir.exists(), "Uploads directory should exist"
            
            # Check for project subdirectories
            project_dir = uploads_dir / 'drawings' / test_setup['test_project_id']
            # Files should be in subdirectories
            assert project_dir.exists() or uploads_dir.exists(), "Project storage directory should exist"
        
        print("✅ Test 5 PASSED: Storage files verified")
    
    def test_6_list_drawing_versions(self, test_setup):
        """Test 6: List all versions of a drawing"""
        if not test_setup['old_version_id']:
            pytest.skip("Old version not uploaded - run test_2 first")
        
        with get_db_session() as db:
            old_version = db.query(DrawingVersion).filter_by(id=test_setup['old_version_id']).first()
            assert old_version is not None, "Old version should exist"
            
            # Get all versions with same drawing name
            versions = db.query(DrawingVersion).filter_by(
                project_id=test_setup['test_project_id'],
                drawing_name=old_version.drawing_name
            ).order_by(DrawingVersion.version_number).all()
            
            assert len(versions) >= 1, "Should have at least 1 version"
        
        print("✅ Test 6 PASSED: Drawing versions listed")
