"""Tests covering the OCR/Diff/Summary pipelines and workers."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Dict
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gcp.database.models import (
    Base,
    ChangeSummary,
    DiffResult,
    Drawing,
    DrawingVersion,
    Job,
    JobStage,
    Project,
    Session,
    User,
)
from processing import DiffPipeline, OCRPipeline, SummaryPipeline
from workers import DiffWorker, OCRWorker, SummaryWorker


class InMemoryStorage:
    """Simple storage stub that keeps artifacts in memory."""

    def __init__(self):
        self.files: Dict[str, bytes] = {}

    def register_file(self, path: str, content: bytes):
        self.files[path] = content

    def download_file(self, path: str) -> bytes:
        return self.files[path]

    def upload_ocr_result(self, drawing_version_id: str, payload: Dict) -> str:
        key = f"ocr/{drawing_version_id}.json"
        self.files[key] = json.dumps(payload).encode("utf-8")
        return key

    def upload_diff_result(self, diff_result_id: str, payload: Dict) -> str:
        key = f"diffs/{diff_result_id}.json"
        self.files[key] = json.dumps(payload).encode("utf-8")
        return key

    def upload_overlay(self, overlay_id: str, payload: Dict) -> str:
        key = f"overlays/{overlay_id}.json"
        self.files[key] = json.dumps(payload).encode("utf-8")
        return key

    def upload_diff_overlay(self, destination_path: str, content: bytes) -> str:
        self.files[destination_path] = content
        return destination_path

    def upload_file(self, file_content: bytes, destination_path: str, content_type: str | None = None, **_: Dict) -> str:
        self.files[destination_path] = file_content if isinstance(file_content, (bytes, bytearray)) else bytes(file_content)
        return destination_path


def _seed_graph(session) -> Dict:
    user = User(id=str(uuid4()), email="demo@example.com", name="Test User")
    project = Project(id=str(uuid4()), user_id=user.id, name="Pipeline Project")
    session_obj = Session(
        id=str(uuid4()),
        user_id=user.id,
        project_id=project.id,
        session_type="comparison",
        status="active",
    )
    session.add_all([user, project, session_obj])
    session.flush()
    return {"user": user, "project": project, "session": session_obj}


def _create_drawing_version(
    session,
    project: Project,
    session_obj: Session,
    *,
    storage_path: str,
    name: str,
    drawing_type: str = "old",
    version_number: int = 1,
):
    drawing = Drawing(
        id=str(uuid4()),
        session_id=session_obj.id,
        drawing_type=drawing_type,
        filename=f"{name}.pdf",
        original_filename=f"{name}.pdf",
        storage_path=storage_path,
        drawing_name=name,
        page_number=1,
    )
    drawing_version = DrawingVersion(
        id=str(uuid4()),
        project_id=project.id,
        drawing_name=name,
        version_number=version_number,
        drawing_id=drawing.id,
    )
    session.add_all([drawing, drawing_version])
    session.flush()
    return drawing_version


@pytest.fixture(scope="module")
def engine():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_database(engine):
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
def storage_stub():
    return InMemoryStorage()


@pytest.fixture(autouse=True)
def stub_pdf_and_alignment(monkeypatch, tmp_path):
    """Avoid expensive external dependencies in pipeline tests."""

    sample_png = tmp_path / 'page.png'

    def _write_sample(path):
        import numpy as np
        import cv2

        img = np.full((128, 128, 3), 255, dtype=np.uint8)
        cv2.rectangle(img, (10, 10), (110, 110), (0, 0, 0), 2)
        cv2.putText(img, 'A101', (15, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.imwrite(str(path), img)

    _write_sample(sample_png)

    def fake_extract(pdf_path):
        return [{'drawing_name': 'A-101', 'page': 1}]

    monkeypatch.setattr(
        'processing.ocr_pipeline.extract_drawing_names',
        fake_extract,
    )
    monkeypatch.setattr(
        'processing.diff_pipeline.extract_drawing_names',
        fake_extract,
    )
    def fake_process_pdf(pdf_path, dpi=300):
        return [str(sample_png)]

    monkeypatch.setattr(
        'processing.ocr_pipeline.process_pdf_with_drawing_names',
        fake_process_pdf,
    )

    def fake_pdf_to_png(source_path, output_path=None, dpi=300, page_number=0):
        target = Path(output_path) if output_path else sample_png
        _write_sample(target)
        return str(target)

    monkeypatch.setattr('processing.diff_pipeline.pdf_to_png', fake_pdf_to_png)

    class _IdentityAligner:
        def align(self, old_img, new_img):
            return new_img

    monkeypatch.setattr('processing.diff_pipeline.AlignDrawings', lambda *_, **__: _IdentityAligner())


def test_ocr_pipeline_updates_version_and_storage(session_factory, storage_stub):
    with session_factory() as session:
        seed = _seed_graph(session)
        drawing_version = _create_drawing_version(
            session,
            seed["project"],
            seed["session"],
            storage_path="source.pdf",
            name="A101",
        )
        drawing_version_id = drawing_version.id
    storage_stub.register_file("source.pdf", b"fake drawing data")
    pipeline = OCRPipeline(storage_service=storage_stub, session_factory=session_factory)

    result = pipeline.run(drawing_version_id)

    assert storage_stub.download_file(result["result_ref"])  # artifact exists
    with session_factory() as session:
        updated = session.get(DrawingVersion, drawing_version_id)
        assert updated.ocr_status == "completed"
        assert updated.ocr_result_ref == result["result_ref"]


def test_diff_and_summary_pipelines(session_factory, storage_stub):
    with session_factory() as session:
        seed = _seed_graph(session)
        old_version = _create_drawing_version(
            session,
            seed["project"],
            seed["session"],
            storage_path="old.pdf",
            name="A102",
        )
        new_version = _create_drawing_version(
            session,
            seed["project"],
            seed["session"],
            storage_path="new.pdf",
            name="A102",
            drawing_type="new",
            version_number=2,
        )
        old_version_id = old_version.id
        new_version_id = new_version.id
        job = Job(
            id=str(uuid4()),
            project_id=seed["project"].id,
            old_drawing_version_id=old_version_id,
            new_drawing_version_id=new_version_id,
            status="in_progress",
            created_by=seed["user"].id,
        )
        session.add(job)
        session.commit()
        job_id = job.id

    storage_stub.register_file("old.pdf", b"old")
    storage_stub.register_file("new.pdf", b"new data")
    ocr = OCRPipeline(storage_service=storage_stub, session_factory=session_factory)
    ocr.run(old_version_id)
    ocr.run(new_version_id)

    diff_pipeline = DiffPipeline(storage_service=storage_stub, session_factory=session_factory)
    diff_run = diff_pipeline.run(job_id, old_version_id, new_version_id)
    assert diff_run["diff_results"], "Diff pipeline should return at least one result"
    primary_diff = diff_run["diff_results"][0]

    with session_factory() as session:
        diff_record = session.get(DiffResult, primary_diff["diff_result_id"])
        assert diff_record is not None
        summary_pipeline = SummaryPipeline(storage_service=storage_stub, session_factory=session_factory)
        summary = summary_pipeline.run(job_id, diff_record.id)
        summary_second = summary_pipeline.run(job_id, diff_record.id)

    with session_factory() as session:
        first = session.get(ChangeSummary, summary["summary_id"])
        latest = session.get(ChangeSummary, summary_second["summary_id"])
        assert first is not None and latest is not None
        assert first.is_active is False
        assert latest.is_active is True
        assert isinstance(latest.summary_text, str)
        assert latest.summary_text != ""


class FakeOrchestrator:
    def __init__(self):
        self.events = []

    def on_ocr_complete(self, job_id, drawing_version_id):
        self.events.append(("ocr", job_id, drawing_version_id))

    def on_diff_complete(self, job_id, diff_results):
        self.events.append(("diff", job_id, diff_results))

    def on_summary_complete(self, job_id):
        self.events.append(("summary", job_id, None))


class FakePipeline:
    def __init__(self, response: Dict):
        self.response = response
        self.calls = []

    def run(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def _seed_job_with_stages(session_factory):
    with session_factory() as session:
        seed = _seed_graph(session)
        old_version = _create_drawing_version(
            session, seed["project"], seed["session"], storage_path="old.pdf", name="A300"
        )
        new_version = _create_drawing_version(
            session,
            seed["project"],
            seed["session"],
            storage_path="new.pdf",
            name="A300",
            drawing_type="new",
            version_number=2,
        )
        old_version_id = old_version.id
        new_version_id = new_version.id
        job = Job(
            id=str(uuid4()),
            project_id=seed["project"].id,
            old_drawing_version_id=old_version_id,
            new_drawing_version_id=new_version_id,
            status="created",
            created_by=seed["user"].id,
        )
        ocr_stage_old = JobStage(
            id=str(uuid4()),
            job_id=job.id,
            stage="ocr",
            drawing_version_id=old_version.id,
            status="pending",
        )
        diff_stage = JobStage(id=str(uuid4()), job_id=job.id, stage="diff", status="pending")
        summary_stage = JobStage(id=str(uuid4()), job_id=job.id, stage="summary", status="pending")
        session.add_all([job, ocr_stage_old, diff_stage, summary_stage])
        session.commit()
        job_id = job.id
    return job_id, old_version_id, new_version_id


def test_ocr_worker_marks_stage_complete(session_factory):
    job_id, drawing_version_id, _ = _seed_job_with_stages(session_factory)
    orchestrator = FakeOrchestrator()
    pipeline = FakePipeline({"result_ref": "ocr/ref"})
    worker = OCRWorker(pipeline=pipeline, orchestrator=orchestrator, session_factory=session_factory)

    worker.process_message({"job_id": job_id, "drawing_version_id": drawing_version_id})

    with session_factory() as session:
        stage = (
            session.query(JobStage)
            .filter_by(job_id=job_id, stage="ocr", drawing_version_id=drawing_version_id)
            .first()
        )
        assert stage.status == "completed"
        assert stage.result_ref == "ocr/ref"
    assert orchestrator.events == [("ocr", job_id, drawing_version_id)]


def test_diff_and_summary_workers_update_stages(session_factory):
    job_id, old_version_id, new_version_id = _seed_job_with_stages(session_factory)
    orchestrator = FakeOrchestrator()
    diff_worker = DiffWorker(
        pipeline=FakePipeline(
            {
                "diff_results": [
                    {
                        "diff_result_id": "diff-1",
                        "result_ref": "diff/ref",
                        "overlay_ref": None,
                        "page_number": 1,
                        "total_pages": 1,
                        "drawing_name": "Sheet 1",
                    }
                ]
            }
        ),
        orchestrator=orchestrator,
        session_factory=session_factory,
    )
    summary_worker = SummaryWorker(
        pipeline=FakePipeline({"summary_id": "summary-1", "summary_text": "text"}),
        orchestrator=orchestrator,
        session_factory=session_factory,
    )

    diff_worker.process_message(
        {"job_id": job_id, "old_drawing_version_id": old_version_id, "new_drawing_version_id": new_version_id}
    )
    summary_worker.process_message(
        {
            "job_id": job_id,
            "diff_result_id": "diff-1",
            "overlay_ref": None,
            "metadata": {'project_id': None, 'page_number': 1, 'total_pages': 1},
        }
    )

    with session_factory() as session:
        diff_stage = session.query(JobStage).filter_by(job_id=job_id, stage="diff").first()
        summary_stage = session.query(JobStage).filter_by(job_id=job_id, stage="summary").first()
        assert diff_stage.status == "completed"
        assert diff_stage.result_ref == '["diff-1"]'
        assert summary_stage.status == "completed"
        assert summary_stage.result_ref == "summary-1"

    assert orchestrator.events[-2:] == [
        ("diff", job_id, [{"diff_result_id": "diff-1", "result_ref": "diff/ref", "overlay_ref": None, "page_number": 1, "total_pages": 1, "drawing_name": "Sheet 1"}]),
        ("summary", job_id, None),
    ]
