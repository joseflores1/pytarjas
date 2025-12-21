# pytarjas/blueprints/artifacts/plannings.py
"""
Plannings API blueprint for managing work plannings and tasks.
Updated to support Planning Templates and dynamic batch metadata.
"""

import uuid
from datetime import datetime, timezone
from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, g, abort
from sqlalchemy.orm import joinedload

from pytarjas.models.user_models import db, User
from pytarjas.models.docs_models import Planning, Task, Form, PlanningTemplate
from pytarjas.auth import login_required, planning_access_required
from pytarjas.helper import wants_json

bp = Blueprint("plannings", __name__, url_prefix="/plannings")

def check_planning_access(planning_id: str) -> Planning:
    """
    Check if current user has access to a planning and return it.
    """
    planning = Planning.query.options(
        joinedload(Planning.planner),
        joinedload(Planning.form),
        joinedload(Planning.template).joinedload(PlanningTemplate.fields),
        joinedload(Planning.tasks)
    ).get_or_404(planning_id)
    
    if g.user.role == "admin":
        return planning
    
    if g.user.role == "planner" and g.user.id == planning.planner_id:
        return planning
    
    abort(403)

@bp.route("/", methods=["GET"])
@login_required
@planning_access_required
def list_plannings():
    """
    List all plannings showing versioned form names and template names.
    """
    status_filter = request.args.get('status', 'all')
    client_search = request.args.get('client_name', '').strip()
    
    query = Planning.query.options(
        joinedload(Planning.planner),
        joinedload(Planning.form),
        joinedload(Planning.template)
    )
    
    if status_filter != 'all':
        query = query.filter(Planning.status == status_filter)
    
    if client_search:
        query = query.filter(Planning.client_name.ilike(f'%{client_search}%'))

    plannings = query.order_by(Planning.created_at.desc()).all()
    
    plannings_data = []
    for plan in plannings:
        plannings_data.append({
            "id": plan.id,
            "client_name": plan.client_name,
            "form_name": plan.form.display_name if plan.form else "N/A",
            "template_name": plan.template.name if plan.template else "Sin Plantilla",
            "status": plan.status,
            "total_tasks": plan.total_tasks,
            "planner": plan.planner.username if plan.planner else "System",
            "created_at": plan.created_at.strftime('%d/%m/%Y %H:%M')
        })
    
    if wants_json():
        return jsonify({
            "success": True,
            "plannings": plannings_data
        })
    
    return render_template(
        "plannings/list_plannings.html",
        plannings=plannings_data,
        status_filter=status_filter,
        client_search=client_search
    )

@bp.route("/create", methods=["GET", "POST"])
@login_required
@planning_access_required
def create_planning():
    """
    Create a new planning using a PlanningTemplate for header metadata and a Form for tasks.
    """
    if request.method == "GET":
        active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
        planning_templates = PlanningTemplate.query.options(
            joinedload(PlanningTemplate.fields)
        ).order_by(PlanningTemplate.name).all()
        
        assignable_users = User.query.filter(
            User.role.in_(["worker", "planner"])
        ).order_by(User.username).all()
        
        if wants_json():
            return jsonify({
                "success": True,
                "forms": [{"id": f.id, "name": f.display_name} for f in active_forms],
                "templates": [
                    {
                        "id": t.id, 
                        "name": t.name, 
                        "fields": [
                            {
                                "name": f.field_name, 
                                "label": f.field_label, 
                                "type": f.field_type, 
                                "required": f.is_required,
                                "options": f.options
                            } 
                            for f in t.fields
                        ]
                    } for t in planning_templates
                ],
                "assignable_users": [{"id": u.id, "username": u.username} for u in assignable_users]
            })
        
        return render_template(
            "plannings/create_plannings.html",
            forms=active_forms,
            planning_templates=planning_templates,
            assignable_users=assignable_users
        )
    
    data = request.get_json() if wants_json() else request.form
    client_name = data.get("client_name")
    form_id = data.get("form_id")
    template_id = data.get("template_id")
    metadata_values = data.get("metadata_values", {})
    records = data.get("records", [])

    if not client_name or not form_id:
        if wants_json():
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        flash("El nombre del cliente y la selección del formulario son obligatorios.", "error")
        return redirect(url_for("plannings.create_planning"))

    try:
        planning = Planning(
            id=str(uuid.uuid4()),
            planner_id=g.user.id,
            form_id=form_id,
            template_id=template_id if template_id else None,
            metadata_values=metadata_values,
            client_name=client_name,
            status="uploaded",
            total_tasks=len(records),
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(planning)
        
        for record in records:
            task_worker_id = record.pop('worker_id', None)
            
            task = Task(
                id=str(uuid.uuid4()),
                planning_id=planning.id,
                form_id=form_id, 
                record_data=record,
                worker_id=task_worker_id,
                created_by_id=g.user.id,
                status="pending",
                responses={},
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(task)
            
        db.session.commit()
        
        if wants_json():
            return jsonify({"success": True, "id": planning.id})
        
        flash("Planificación creada exitosamente.", "success")
        return redirect(url_for("plannings.list_plannings"))
        
    except Exception as e:
        db.session.rollback()
        if wants_json():
            return jsonify({"success": False, "error": str(e)}), 500
        
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("plannings.create_planning"))

@bp.route("/<planning_id>")
@login_required
@planning_access_required
def get_planning(planning_id):
    """
    View details of a specific planning, including metadata and generated tasks.
    """
    planning = check_planning_access(planning_id)
    
    if wants_json():
        return jsonify({
            "success": True,
            "planning": {
                "id": planning.id,
                "client_name": planning.client_name,
                "form_version": planning.form.display_name if planning.form else "N/A",
                "template_name": planning.template.name if planning.template else "Sin Plantilla",
                "metadata": planning.metadata_values,
                "status": planning.status,
                "tasks_count": len(planning.tasks),
                "created_at": planning.created_at.strftime('%d/%m/%Y %H:%M')
            }
        })
    
    return render_template(
        "plannings/edit_plannings.html",
        planning=planning
    )