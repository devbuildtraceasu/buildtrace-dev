"""Tests for the drawing upload service."""

from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gcp.database.models import Base, Drawing, DrawingVersion, Project, User
from services.drawing_service import DrawingUploadError, DrawingUploadService


class DummyStorage:
    """Stub storage backend used for unit tests."""

    def __init__(self):
        self.uploads = []

    def upload_file(self, file_content, destination_path, content_type=None):
        self.uploads.append(
            {
                'bytes': file_content,
                'path': destination_path,
                'content_type': content_type,
            }
        )
        return f"local://{destination_path}"


@pytest.fixture(scope='module')
def engine():
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_database(engine):
    """Ensure each test starts with a clean schema."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def session_factory(engine):
    SessionLocal = sessionmaker(bind=engine)

    @contextmanager
    def _session_scope():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    return _session_scope


@pytest.fixture
def project_fixture(session_factory):
    with session_factory() as session:
        user = User(id='user-1', email='demo@example.com', name='Demo User')
        project = Project(id='project-1', user_id=user.id, name='Demo Project')
        session.add_all([user, project])
        session.flush()
        project_id = project.id
        user_id = user.id
    return {'project_id': project_id, 'user_id': user_id}


def test_handle_upload_persists_drawing_version(session_factory, project_fixture):
    storage = DummyStorage()
    service = DrawingUploadService(storage_service_instance=storage, session_factory=session_factory)

    result = service.handle_upload(
        file_bytes=b'%PDF-1.4 fake content',
        filename='A101.pdf',
        content_type='application/pdf',
        project_id=project_fixture['project_id'],
        user_id=project_fixture['user_id'],
        is_revision=False,
    )

    assert result.version_number == 1
    assert storage.uploads[0]['path'].startswith('drawings/')
    assert storage.uploads[0]['bytes'] == b'%PDF-1.4 fake content'

    with session_factory() as session:
        assert session.query(DrawingVersion).count() == 1
        drawing = session.query(Drawing).first()
        assert drawing is not None
        assert drawing.session_id is not None
        assert drawing.drawing_type == 'old'


def test_handle_upload_missing_project(session_factory):
    storage = DummyStorage()
    service = DrawingUploadService(storage_service_instance=storage, session_factory=session_factory)

    with pytest.raises(DrawingUploadError) as exc:
        service.handle_upload(
            file_bytes=b'abc',
            filename='missing.pdf',
            content_type='application/pdf',
            project_id='unknown-project',
            user_id='user-1',
            is_revision=False,
        )

    assert exc.value.status_code == 404


def test_revision_upload_marks_drawing_as_new(session_factory, project_fixture):
    storage = DummyStorage()
    service = DrawingUploadService(storage_service_instance=storage, session_factory=session_factory)

    service.handle_upload(
        file_bytes=b'new revision bytes',
        filename='A101.pdf',
        content_type='application/pdf',
        project_id=project_fixture['project_id'],
        user_id=project_fixture['user_id'],
        is_revision=True,
    )

    with session_factory() as session:
        drawing = session.query(Drawing).first()
        assert drawing.drawing_type == 'new'


def test_handle_upload_creates_placeholder_user(session_factory):
    storage = DummyStorage()
    service = DrawingUploadService(storage_service_instance=storage, session_factory=session_factory)

    with session_factory() as session:
        owner = User(id='owner-1', email='owner@example.com', name='Owner')
        project = Project(id='project-placeholder', user_id=owner.id, name='Placeholder Project')
        session.add_all([owner, project])

    service.handle_upload(
        file_bytes=b'data',
        filename='A200.pdf',
        content_type='application/pdf',
        project_id='project-placeholder',
        user_id='missing-user',
        is_revision=False,
    )

    with session_factory() as session:
        placeholder = session.query(User).filter_by(id='missing-user').first()
        assert placeholder is not None
        assert placeholder.email.endswith('@system.local')
