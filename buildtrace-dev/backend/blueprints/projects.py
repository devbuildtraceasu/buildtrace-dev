"""Projects blueprint for CRUD operations."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import asc

try:
    from gcp.database import get_db_session
    from gcp.database.models import Project, Organization, User
    DB_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    DB_AVAILABLE = False
    raise_exc = exc

projects_bp = Blueprint('projects', __name__, url_prefix='/api/v1/projects')


def _serialize_project(project: Project) -> dict:
    return {
        'project_id': project.id,
        'name': project.name,
        'description': project.description,
        'project_number': project.project_number,
        'client_name': project.client_name,
        'location': project.location,
        'status': project.status,
        'user_id': project.user_id,
        'organization_id': project.organization_id,
        'created_at': project.created_at.isoformat() if project.created_at else None,
        'updated_at': project.updated_at.isoformat() if project.updated_at else None,
    }


@projects_bp.route('', methods=['GET'])
def list_projects():
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    user_id = request.args.get('user_id')
    org_id = request.args.get('organization_id')
    with get_db_session() as db:
        query = db.query(Project).order_by(asc(Project.created_at))
        if user_id:
            query = query.filter(Project.user_id == user_id)
        if org_id:
            query = query.filter(Project.organization_id == org_id)
        projects = query.all()
        return jsonify({'projects': [_serialize_project(p) for p in projects]})


@projects_bp.route('', methods=['POST'])
def create_project():
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    data = request.get_json() or {}
    name = data.get('name')
    user_id = data.get('user_id')
    if not name or not user_id:
        return jsonify({'error': 'name and user_id are required'}), 400
    with get_db_session() as db:
        owner = db.query(User).filter_by(id=user_id).first()
        if not owner:
            return jsonify({'error': 'User not found'}), 404
        project = Project(
            name=name,
            user_id=user_id,
            description=data.get('description'),
            project_number=data.get('project_number'),
            client_name=data.get('client_name'),
            location=data.get('location'),
            status=data.get('status', 'active'),
            organization_id=data.get('organization_id') or owner.organization_id,
        )
        db.add(project)
        db.flush()
        current_app.logger.info('Project created', extra={'project_id': project.id})
        return jsonify({'project': _serialize_project(project)}), 201


@projects_bp.route('/<project_id>', methods=['GET'])
def get_project(project_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        return jsonify({'project': _serialize_project(project)})


@projects_bp.route('/<project_id>', methods=['PUT'])
def update_project(project_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    data = request.get_json() or {}
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        for field in ['name', 'description', 'project_number', 'client_name', 'location', 'status']:
            if field in data:
                setattr(project, field, data[field])
        if 'organization_id' in data:
            project.organization_id = data['organization_id']
        db.flush()
        return jsonify({'project': _serialize_project(project)})


@projects_bp.route('/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        db.delete(project)
        return jsonify({'status': 'deleted'})


@projects_bp.route('/<project_id>/members', methods=['GET'])
def list_project_members(project_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        owner = db.query(User).filter_by(id=project.user_id).first()
        members = []
        if owner:
            members.append({
                'user_id': owner.id,
                'name': owner.name,
                'email': owner.email,
                'role': owner.role or 'owner'
            })
        return jsonify({'project_id': project_id, 'members': members})
