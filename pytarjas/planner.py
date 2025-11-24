# pytarjas/planner.py
"""
Planner blueprint for managing work planifications and documents.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, g, abort, current_app
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
import uuid
from functools import wraps
from sqlalchemy import cast, Date, or_

# Import database and models
from pytarjas.models.user_models import db, User
from pytarjas.models.docs_models import Planification, Document, Form, Question 

# Import authentication decorators
from pytarjas.auth import login_required

# Import helper functions
from pytarjas.helper import wants_json

# Create blueprint with URL prefix /planner
bp = Blueprint("planner", __name__, url_prefix="/planner")


# ============================================================================
# DECORATOR HELPERS
# ============================================================================

def check_planification_access(planification_id: str) -> Planification:
    """
    Check if current user has access to a planification and return it.
    """
    planification = Planification.query.options(
        joinedload(Planification.planner),
        joinedload(Planification.form),
        joinedload(Planification.documents)
    ).get_or_404(planification_id)
    
    if g.user.role == "admin":
        return planification
    
    elif g.user.role == "planner" and g.user.id == planification.planner_id:
        return planification
    
    else:
        abort(403)


def planification_access_required(view):
    """
    Decorator to require planification access permissions.
    """
    
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user.role == "client" or g.user.role == "worker":
            if wants_json():
                return jsonify({
                    "success": False,
                    "error": "Access denied. Clients cannot access planifications."
                }), 403
            else:
                abort(403)
        
        return view(**kwargs)
    
    return wrapped_view


# ============================================================================
# ROUTE: Homepage/Dashboard (Placeholder)
# ============================================================================

@bp.route("/") # NEW: The root /planner/ is now the homepage
@login_required
def index():
    """
    Planner Dashboard - Placeholder page.
    """
    if wants_json():
         return jsonify({"success": True, "message": "Planner Dashboard accessed"}), 200
    
    # Renders the new placeholder template
    return render_template("planner/index.html", user=g.user)


# ============================================================================
# ROUTE: List all planifications (The actual list content)
# ============================================================================

@bp.route("/list") 
@login_required
@planification_access_required
def list_planifications():
    """
    List all planifications (Actual list page).
    """
    status_filter = request.args.get('status', 'all')
    planner_id_filter = request.args.get('planner_id')
    form_id_filter=request.args.get("form_id")
    client_name_search = request.args.get('client_name', '').strip()
    form_type_filter = request.args.get('form_type')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    query = Planification.query.options(
        joinedload(Planification.planner),
        joinedload(Planification.form),
        joinedload(Planification.documents)
    )
    
    if status_filter != 'all':
        query = query.filter(Planification.status == status_filter)
    
    if planner_id_filter and g.user.role in ['admin', 'planner']:
        query = query.filter(Planification.planner_id == planner_id_filter)
    
    if client_name_search:
        query = query.filter(Planification.client_name.ilike(f'%{client_name_search}%'))
    
    if form_type_filter:
        query = query.join(Form).filter(Form.form_type == form_type_filter)
    
    if form_id_filter:
        query = query.filter(Planification.form_id == form_id_filter)

    total = query.count()
    
    planifications = query.order_by(
        Planification.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    planifications_data = []
    for plan in planifications:
        completed_docs = sum(
            1 for doc in plan.documents 
            if doc.status == 'completed'
        )
        
        plan_dict = {
            "id": plan.id,
            "client_name": plan.client_name,
            "form_name": plan.form.name if plan.form else None,
            "form_type": plan.form.form_type if plan.form else None,
            "status": plan.status,
            "total_documents": plan.total_documents,
            "completed_documents": completed_docs,
            "planner": {
                "id": plan.planner.id,
                "username": plan.planner.username
            } if plan.planner else None,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
            "_planification": plan
        }
        planifications_data.append(plan_dict)
    
    if wants_json():
        return jsonify({
            "success": True,
            "planifications": planifications_data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "status": status_filter if status_filter != 'all' else None,
                "planner_id": planner_id_filter,
                "client_name": client_name_search if client_name_search else None,
                "form_type": form_type_filter
            }
        }), 200
    
    planners = []
    if g.user.role in ['admin', 'planner']:
        planners = User.query.filter_by(role='planner').all()
    
    form_types = db.session.query(Form.form_type).distinct().all()
    form_types = [ft[0] for ft in form_types if ft[0]]
    
    return render_template(
        "planner/list_planifications.html", # FIX TEMPLATE PATH
        planifications=planifications_data,
        total=total,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
        planner_id_filter=planner_id_filter,
        client_name_search=client_name_search,
        form_type_filter=form_type_filter,
        planners=planners,
        form_types=form_types,
        user=g.user
    )


# ============================================================================
# ROUTE: Get single planification with details (Remaining routes adjusted)
# ============================================================================

@bp.route("/<planification_id>", methods=["GET"])
@login_required
@planification_access_required
def get_planification(planification_id):
    planification = check_planification_access(planification_id)
    
    progress = {
        "total": planification.total_documents,
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
        "reviewed": 0,
        "approved": 0
    }
    
    for document in planification.documents:
        status = document.status
        if status in progress:
            progress[status] += 1
        else:
            progress["pending"] += 1
    
    documents_data = []
    for document in planification.documents:
        doc_dict = {
            "id": document.id,
            "record_data": document.record_data,
            "status": document.status,
            "worker": {
                "id": document.worker.id,
                "username": document.worker.username
            } if document.worker else None,
            "started_at": document.started_at.isoformat() if document.started_at else None,
            "completed_at": document.completed_at.isoformat() if document.completed_at else None,
            "is_synced": document.is_synced,
            "created_at": document.created_at.isoformat() if document.created_at else None
        }
        
        documents_data.append(doc_dict)
    
    if wants_json():
        return jsonify({
            "success": True,
            "planification": {
                "id": planification.id,
                "client_name": planification.client_name,
                "status": planification.status,
                "total_documents": planification.total_documents,
                "file_name": planification.file_name if planification.file_name else None,
                "form": {
                    "id": planification.form.id,
                    "name": planification.form.name,
                    "form_type": planification.form.form_type,
                    "description": planification.form.description,
                    "questions": [
                        {
                            "id": q.id,
                            "question_text": q.question_text,
                            "question_type": q.question_type,
                            "is_required": q.is_required,
                            "order": q.order,
                            "options": q.options
                        }
                        for q in sorted(planification.form.questions, key=lambda x: x.order)
                    ]
                } if planification.form else None,
                "documents": documents_data,
                "planner": {
                    "id": planification.planner.id,
                    "username": planification.planner.username,
                    "email": planification.planner.email
                } if planification.planner else None,
                "progress": progress,
                "created_at": planification.created_at.isoformat() if planification.created_at else None,
                "updated_at": planification.updated_at.isoformat() if planification.updated_at else None
            }
        }), 200
    
    return render_template(
        "planner/view_planification.html", # FIX TEMPLATE PATH
        planification=planification,
        documents=documents_data,
        progress=progress,
        user=g.user
    )


# ============================================================================
# ROUTE: Create new planification
# ============================================================================

@bp.route("/create", methods=["GET", "POST"])
@login_required
@planification_access_required
def create_planification():
    if g.user.role not in ['planner', 'admin']:
        error_msg = "Access denied. Only planners and admins can create planifications."
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 403
        else:
            flash(error_msg, "error")
            return redirect(url_for("planner.list_planifications"))
    
    if request.method == "GET":
        if wants_json():
            active_forms = Form.query.filter_by(is_active=True).all()
            return jsonify({
                "success": True,
                "available_forms": [
                    {
                        "id": form.id,
                        "name": form.name,
                        "form_type": form.form_type,
                        "description": form.description
                    }
                    for form in active_forms
                ]
            }), 200
        else:
            active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
            return render_template(
                "planner/create_planification.html", # FIX TEMPLATE PATH
                forms=active_forms,
                user=g.user
            )
    
    error = None
    
    if wants_json():
        data = request.get_json()
        client_name = data.get("client_name", "").strip()
        form_id = data.get("form_id")
        records_data = data.get("records", [])
        status = data.get("status", "uploaded")
    else:
        client_name = request.form.get("client_name", "").strip()
        form_id = request.form.get("form_id")
        status = request.form.get("status", "uploaded")
        
        records_data = []
        record_index = 0
        
        while True:
            record_field_key = f"record_{record_index}_data"
            
            if record_field_key not in request.form:
                break
            
            record_data = {}
            prefix = f"record_{record_index}_"
            
            for key in request.form.keys():
                if key.startswith(prefix):
                    field_name = key[len(prefix):]
                    record_data[field_name] = request.form.get(key)
            
            if record_data:
                records_data.append(record_data)
            
            record_index += 1
    
    if not client_name:
        error = "Client name is required."
    elif not form_id:
        error = "Form selection is required."
    elif not records_data or len(records_data) == 0:
        error = "At least one record is required."
    else:
        form = Form.query.filter_by(id=form_id, is_active=True).first()
        if not form:
            error = "Form not found or inactive."
    
    if error is None:
        try:
            planification = Planification(
                id=str(uuid.uuid4()),
                planner_id=g.user.id,
                form_id=form_id,
                client_name=client_name,
                status=status,
                total_documents=len(records_data),
                file_path="",
                file_name="",
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(planification)
            
            created_documents = []
            for record_data in records_data:
                document = Document(
                    id=str(uuid.uuid4()),
                    planification_id=planification.id,
                    form_id=form_id,
                    record_data=record_data,
                    created_by_id=g.user.id,
                    worker_id=None,
                    status="pending",
                    responses={},
                    photos=[],
                    is_synced=True,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(document)
                created_documents.append(document)
            
            planification.total_documents = len(records_data)
            planification.status = "completed"
            planification.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            success_message = (
                f"Planification created successfully with {len(records_data)} documents."
            )
            
            if wants_json():
                return jsonify({
                    "success": True,
                    "message": success_message,
                    "planification": {
                        "id": planification.id,
                        "client_name": planification.client_name,
                        "total_documents": planification.total_documents,
                        "status": planification.status,
                        "created_at": planification.created_at.isoformat()
                    }
                }), 201
            else:
                flash(success_message, "success")
                return redirect(url_for("planner.get_planification", planification_id=planification.id))
        
        except Exception as e:
            db.session.rollback()
            error = f"An error occurred while creating planification: {str(e)}"
    
    if wants_json():
        return jsonify({
            "success": False,
            "error": error
        }), 400
    else:
        flash(error, "error")
        active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
        return render_template(
            "planner/create_planification.html", # FIX TEMPLATE PATH
            forms=active_forms,
            user=g.user,
            error=error
        )


# ============================================================================
# ROUTE: Delete planification
# ============================================================================

@bp.route("/<planification_id>/delete", methods=["POST", "DELETE"])
@login_required
@planification_access_required
def delete_planification(planification_id):
    if g.user.role not in ['planner', 'admin']:
        error_msg = "Access denied. Only planners and admins can delete planifications."
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 403
        else:
            flash(error_msg, "error")
            return redirect(url_for("planner.list_planifications"))
    
    planification = check_planification_access(planification_id)
    
    if g.user.role == 'planner' and planification.planner_id != g.user.id:
        error_msg = "Access denied. You can only delete planifications you created."
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 403
        else:
            flash(error_msg, "error")
            return redirect(url_for("planner.list_planifications"))
    
    try:
        planification.status = "deleted"
        planification.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        success_message = f"Planification '{planification.client_name}' deleted successfully."
        
        if wants_json():
            return jsonify({
                "success": True,
                "message": success_message
            }), 200
        else:
            flash(success_message, "success")
            return redirect(url_for("planner.list_planifications"))
    
    except Exception as e:
        db.session.rollback()
        error_message = f"An error occurred: {str(e)}"
        
        if wants_json():
            return jsonify({
                "success": False,
                "error": error_message
            }), 500
        else:
            flash(error_message, "error")
            return redirect(url_for("planner.list_planifications"))


# ============================================================================
# ROUTE: Update planification status
# ============================================================================

@bp.route("/<planification_id>/status", methods=["PUT", "PATCH"])
@login_required
@planification_access_required
def update_planification_status(planification_id):
    if g.user.role not in ['planner', 'admin']:
        return jsonify({
            "success": False,
            "error": "Access denied. Only planners and admins can update status."
        }), 403
    
    if not wants_json():
        return jsonify({
            "success": False,
            "error": "This endpoint only accepts JSON requests."
        }), 400
    
    planification = check_planification_access(planification_id)
    
    data = request.get_json()
    new_status = data.get("status")
    
    valid_statuses = ["uploaded", "processing", "completed", "error", "deleted"]
    if not new_status or new_status not in valid_statuses:
        return jsonify({
            "success": False,
            "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        }), 400
    
    try:
        old_status = planification.status
        planification.status = new_status
        planification.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Status updated from '{old_status}' to '{new_status}'.",
            "planification": {
                "id": planification.id,
                "status": planification.status,
                "updated_at": planification.updated_at.isoformat()
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Database error: {str(e)}"
        }), 500