# pytarjas/tasks.py
"""
Tasks API blueprint for managing documents/tasks.

Updates:
- Fixed list_tasks query to use joinedload (prevents hidden tasks due to join issues)
- create_task redirects to list_tasks on success
"""

from flask import Blueprint, request, jsonify, render_template, g, abort, redirect, url_for, flash
from datetime import datetime, timezone
from pytarjas.auth import login_required, task_access_required
from pytarjas.models.user_models import User, db
from pytarjas.models.docs_models import Document, Planification, Form, Question #noqa
from pytarjas.helper import wants_json
import uuid

# Create blueprint with URL prefix /tasks
bp = Blueprint("tasks", __name__, url_prefix="/tasks")


@bp.route("/create", methods=["GET", "POST"])
@login_required
@task_access_required
def create_task():
    """
    Create a standalone task (not from planification).
    """
    if request.method == "GET":
        # Get active forms
        active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
        
        # Get assignable users based on role
        assignable_users = []
        if g.user.role == "worker":
            assignable_users = [g.user]
        elif g.user.role == "planner":
            assignable_users = User.query.filter(
                User.role.in_(["worker", "planner"])
            ).order_by(User.username).all()
        elif g.user.role == "admin":
            assignable_users = User.query.filter(
                User.role.in_(["worker", "planner", "admin"])
            ).order_by(User.username).all()
        
        if wants_json():
            return jsonify({
                "success": True,
                "forms": [{"id": f.id, "name": f.name, "type": f.form_type} for f in active_forms],
                "assignable_users": [{"id": u.id, "username": u.username, "role": u.role} for u in assignable_users]
            }), 200
        else:
            return render_template(
                "tasks/create_task.html",
                forms=active_forms,
                assignable_users=assignable_users,
                user=g.user
            )
    
    # POST: Create the task
    if wants_json():
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    form_id = data.get("form_id")
    worker_id = data.get("worker_id")
    
    # Validation
    if not form_id:
        return (jsonify({"success": False, "error": "Form is required"}), 400) if wants_json() else abort(400)
    
    form = Form.query.filter_by(id=form_id, is_active=True).first()
    if not form:
        return (jsonify({"success": False, "error": "Form not found"}), 404) if wants_json() else abort(404)
    
    if not worker_id:
        worker_id = g.user.id
    
    # Create the document
    document = Document(
        id=str(uuid.uuid4()),
        planification_id=None,
        form_id=form_id,
        record_data={},
        worker_id=worker_id,
        created_by_id=g.user.id,
        status="pending",
        responses={},
        photos=[],
        is_synced=True,
        created_at=datetime.now(timezone.utc)
    )
    
    try:
        db.session.add(document)
        db.session.commit()
        
        if wants_json():
            return jsonify({
                "success": True,
                "message": "Task created successfully",
                "task_id": document.id
            }), 201
        else:
            flash("Tarea creada exitosamente", "success")
            # CHANGE: Redirect to list_tasks instead of get_task for better flow
            return redirect(url_for("tasks.list_tasks"))
    
    except Exception as e:
        db.session.rollback()
        return (jsonify({"success": False, "error": str(e)}), 500) if wants_json() else abort(500)


@bp.route("/", methods=["GET"])
@login_required
@task_access_required
def list_tasks():
    """
    Get list of tasks with role-based filtering.
    """
    status = request.args.get('status', 'all')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    worker_id_filter = request.args.get('worker_id')
    
    # FIX: Use joinedload instead of explicit joins to avoid filtering issues
    # This ensures we get the documents and populate related fields efficiently
    query = Document.query.options(
        db.joinedload(Document.form),
        db.joinedload(Document.planification),
        db.joinedload(Document.worker),
        db.joinedload(Document.created_by)
    )
    
    # Role-based filtering
    if g.user.role == "worker":
        query = query.filter(
            db.or_(
                Document.worker_id == g.user.id,
                Document.created_by_id == g.user.id
            )
        )
    elif g.user.role in ["planner", "admin"]:
        if worker_id_filter:
            query = query.filter(Document.worker_id == worker_id_filter)
    
    if status != 'all':
        query = query.filter(Document.status == status)
    
    total = query.count()
    documents = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    
    tasks = []
    for doc in documents:
        task_data = {
            "id": doc.id,
            "record_data": doc.record_data or {},
            "status": doc.status,
            "worker": {"username": doc.worker.username} if doc.worker else None,
            # Safe access to form fields
            "form_type": doc.form.form_type if doc.form else "Unknown",
            "form_name": doc.form.name if doc.form else "Deleted Form",
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "started_at": doc.started_at.isoformat() if doc.started_at else None,
            "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
            "_document": doc
        }
        tasks.append(task_data)
    
    if wants_json():
        return jsonify({
            "success": True,
            "tasks": tasks,
            "total": total
        }), 200
    
    return render_template(
        "tasks/task_list.html",
        tasks=tasks,
        status=status,
        total=total,
        offset=offset,
        limit=limit,
        user=g.user
    )


@bp.route("/<task_id>", methods=["GET"])
@login_required
@task_access_required
def get_task(task_id):
    document = Document.query.options(
        db.joinedload(Document.form).joinedload(Form.questions),
        db.joinedload(Document.planification),
        db.joinedload(Document.worker)
    ).filter_by(id=task_id).first()  

    if not document:
        return (jsonify({"success": False, "error": "Task not found"}), 404) if wants_json() else abort(404)
    
    if g.user.role == "worker" and document.worker_id != g.user.id:
        return (jsonify({"success": False, "error": "Access denied"}), 403) if wants_json() else abort(403)
    
    questions = []
    # Handle case where form might have been deleted/detached (unlikely but safe)
    if document.form:
        for q in sorted(document.form.questions, key=lambda x: x.order):
            questions.append({
                "id": q.id,
                "text": q.question_text,
                "type": q.question_type,
                "is_required": q.is_required,
                "order": q.order,
                "options": q.options or {},
                "_question": q
            })
    
    task_data = {
        "id": document.id,
        "status": document.status,
        "record_data": document.record_data or {},
        "form": {
            "id": document.form.id if document.form else None,
            "name": document.form.name if document.form else "Deleted Form",
            "type": document.form.form_type if document.form else "unknown",
            "questions": questions
        },
        "responses": document.responses or {},
        "photos": document.photos or [],
        "worker": {"id": document.worker.id, "username": document.worker.username} if document.worker else None,
        "timestamps": {
            "created_at": document.created_at.isoformat() if document.created_at else None,
        },
        "_document": document
    }
    
    if wants_json():
        return jsonify({"success": True, "task": task_data}), 200
    
    return render_template("tasks/task_detail.html", task=task_data, user=g.user)


@bp.route("/<task_id>/update", methods=["PUT", "PATCH"])
@login_required
@task_access_required
def update_task(task_id):
    if not request.is_json:
        return jsonify({"success": False, "error": "JSON required"}), 400
    
    document = Document.query.get(task_id)
    if not document:
        return jsonify({"success": False, "error": "Task not found"}), 404
        
    if g.user.role == "worker" and document.worker_id != g.user.id:
        return jsonify({"success": False, "error": "Access denied"}), 403
    
    data = request.get_json()
    
    if "status" in data:
        new_status = data["status"]
        old_status = document.status
        document.status = new_status
        
        if new_status == "in_progress" and old_status == "pending":
            if not document.worker_id:
                document.worker_id = g.user.id
            if not document.started_at:
                document.started_at = datetime.now(timezone.utc)
        elif new_status == "completed":
            if not document.completed_at:
                document.completed_at = datetime.now(timezone.utc)
    
    if "responses" in data:
        if document.responses is None:
            document.responses = {}
        document.responses.update(data["responses"])
        db.session.query(Document).filter_by(id=task_id).update(
            {"responses": document.responses}, synchronize_session=False
        )
    
    if "photos" in data:
        if document.photos is None:
            document.photos = []
        document.photos.extend(data["photos"])
        db.session.query(Document).filter_by(id=task_id).update(
            {"photos": document.photos}, synchronize_session=False
        )
        
    document.updated_at = datetime.now(timezone.utc)
    document.is_synced = data.get("mark_synced", False)
    
    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Updated"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500