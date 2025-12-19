# pytarjas/blueprints/artifacts/forms.py
"""
Forms blueprint for managing Form templates and Questions.

This blueprint allows Admins, Planners, and Workers to create and manage
form templates that will be used for tarja tasks during field work.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, g
from sqlalchemy import insert
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
import uuid
import json
from pytarjas.models.user_models import db
from pytarjas.models.docs_models import Form, Question, Task, Planning
from pytarjas.auth import login_required, form_access_required

bp = Blueprint("forms", __name__, url_prefix="/forms")

def get_existing_form_types():
    """Fetches all unique form types currently in the database."""
    types = {"consolidado", "desconsolidado"}
    try:
        db_types = db.session.query(Form.form_type).distinct().all()
        for t in db_types:
            if t[0]:
                types.add(t[0])
    except Exception:
        # Fallback to defaults if DB fails
        pass
    return sorted(list(types))

# ============================================================================
# ROUTE: List all forms
# ============================================================================
@bp.route("/")
@login_required
@form_access_required
def list_forms():
    form_type_filter = request.args.get("form_type")
    is_active_filter = request.args.get("is_active")
    
    # Base query: Order by Name ASC, then Version DESC (so v2 appears before v1)
    query = Form.query.order_by(Form.name.asc(), Form.version.desc())

    if form_type_filter:
        query = query.filter_by(form_type=form_type_filter)
    
    if is_active_filter:
        is_active_bool = is_active_filter.lower() == "true"
        query = query.filter_by(is_active=is_active_bool)
    else:
        # Default: Show only active forms in UI lists unless specifically requested
        query = query.filter_by(is_active=True)
    
    forms = query.all()
    
    if request.is_json:
        return jsonify({
            "success": True,
            "forms": [
                {
                    "id": form.id,
                    "name": form.name,
                    "version": form.version,
                    "display_name": form.display_name,
                    "description": form.description,
                    "form_type": form.form_type,
                    "is_active": form.is_active,
                    "updated_at": form.updated_at.isoformat() if form.updated_at else None,
                    "question_count": len(form.questions)
                } for form in forms
            ]
        }), 200
    
    return render_template(
        "forms/list_forms.html",
        forms=forms,
        form_type_filter=form_type_filter,
        is_active_filter=is_active_filter or "true"
    )

# ============================================================================
# ROUTE: Create new form
# ============================================================================
@bp.route("/create", methods=["GET", "POST"])
@login_required
@form_access_required
def create_form():
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            name = data.get("name")
            description = data.get("description")
            form_type = data.get("form_type")
            questions_data = data.get("questions", [])
        else: 
            name = request.form.get("name")
            description = request.form.get("description")
            form_type = request.form.get("form_type")
            questions_data = []
            question_ids = request.form.getlist("question_ids[]")
            
            for q_id in question_ids:
                options_str = request.form.get(f"question_options_{q_id}")
                try:
                    if options_str:
                        options_dict = json.loads(options_str)
                    else:
                        options_dict = None
                except Exception:
                    options_dict = None
                
                questions_data.append({
                    "question_text": request.form.get(f"question_text_{q_id}"),
                    "question_description": request.form.get(f"question_description_{q_id}"),
                    "question_type": request.form.get(f"question_type_{q_id}"),
                    "order": int(request.form.get(f"question_order_{q_id}", 0)),
                    "is_required": request.form.get(f"question_required_{q_id}") == "true",
                    "options": options_dict
                })
        
        error = None
        if not name:
            error = "Name is required."
        else:
            # Check for duplicates ONLY among active forms
            exists = Form.query.filter_by(name=name, is_active=True).first()
            if exists:
                error = f"Form '{name}' already exists (Active)."

        if not error:
            try:
                new_form = Form(
                    name=name,
                    version=1,
                    description=description,
                    form_type=form_type,
                    is_active=True,
                    created_by_id=g.user.id
                )
                db.session.add(new_form)
                db.session.flush()
                
                if questions_data:
                    q_inserts = []
                    for q in questions_data:
                        q_inserts.append({
                            "id": str(uuid.uuid4()),
                            "form_id": new_form.id,
                            "question_text": q.get("question_text"),
                            "question_description": q.get("question_description"),
                            "question_type": q.get("question_type"),
                            "is_required": q.get("is_required", True),
                            "order": q.get("order", 0),
                            "options": q.get("options"),
                            "created_at": datetime.now(timezone.utc)
                        })
                    db.session.execute(insert(Question), q_inserts)
                
                db.session.commit()
                msg = f"Form '{name}' created."
                
                if request.is_json:
                    return jsonify({"success": True, "message": msg})
                
                return redirect(url_for("forms.list_forms"))
                    
            except Exception as e:
                db.session.rollback()
                error = str(e)
        
        if request.is_json:
            return jsonify({"success": False, "error": error}), 400
        
        flash(error, "error")

    existing_types = get_existing_form_types()
    return render_template("forms/create_forms.html", existing_types=existing_types)

# ============================================================================
# ROUTE: Edit existing form (VERSIONING LOGIC)
# ============================================================================
@bp.route("/<form_id>/edit", methods=["GET", "PUT", "POST"])
@login_required
@form_access_required
def edit_form(form_id):
    form = Form.query.options(joinedload(Form.questions)).get_or_404(form_id)
    
    if request.method in ["POST", "PUT"]:
        if request.is_json:
            data = request.get_json()
            name = data.get("name", form.name)
            description = data.get("description", form.description)
            form_type = data.get("form_type", form.form_type)
            questions_data = data.get("questions")
        else:
            name = request.form.get("name", form.name)
            description = request.form.get("description", form.description)
            form_type = request.form.get("form_type", form.form_type)
            
            questions_data = []
            question_ids = request.form.getlist("question_ids[]")
            for q_id in question_ids:
                options_str = request.form.get(f"question_options_{q_id}")
                try:
                    if options_str:
                        options_dict = json.loads(options_str)
                    else:
                        options_dict = None
                except Exception:
                    options_dict = None

                questions_data.append({
                    "id": q_id, 
                    "question_text": request.form.get(f"question_text_{q_id}"),
                    "question_description": request.form.get(f"question_description_{q_id}"),
                    "question_type": request.form.get(f"question_type_{q_id}"),
                    "order": int(request.form.get(f"question_order_{q_id}", 0)),
                    "is_required": request.form.get(f"question_required_{q_id}") == "true",
                    "options": options_dict
                })

        # Name uniqueness check (if changed)
        if name != form.name:
            exists = Form.query.filter_by(name=name, is_active=True).first()
            if exists:
                msg = f"Name '{name}' is taken."
                if request.is_json:
                    return jsonify({"success": False, "error": msg})
                
                flash(msg, "error")
                return redirect(url_for("forms.edit_form", form_id=form_id))

        try:
            # Check for existing dependencies to decide on versioning
            has_tasks = db.session.query(Task).filter_by(form_id=form.id).first() is not None
            has_plannings = db.session.query(Planning).filter_by(form_id=form.id).first() is not None
            
            if has_tasks or has_plannings:
                # ARCHIVE AND CLONE (VERSIONING)
                form.is_active = False
                form.updated_at = datetime.now(timezone.utc)
                
                new_version = form.version + 1
                new_form = Form(
                    name=name,
                    version=new_version,
                    description=description,
                    form_type=form_type,
                    is_active=True,
                    created_by_id=g.user.id
                )
                db.session.add(new_form)
                db.session.flush()
                
                if questions_data:
                    q_inserts = []
                    for q in questions_data:
                        q_inserts.append({
                            "id": str(uuid.uuid4()),
                            "form_id": new_form.id,
                            "question_text": q.get("question_text"),
                            "question_description": q.get("question_description"),
                            "question_type": q.get("question_type"),
                            "is_required": q.get("is_required", True),
                            "order": q.get("order", 0),
                            "options": q.get("options"),
                            "created_at": datetime.now(timezone.utc)
                        })
                    db.session.execute(insert(Question), q_inserts)
                
                msg = f"Form updated to Version {new_version}."
            else:
                # UPDATE IN PLACE
                form.name = name
                form.description = description
                form.form_type = form_type
                form.updated_at = datetime.now(timezone.utc)
                
                if questions_data is not None:
                    existing_ids = {q.id for q in form.questions}
                    incoming_ids = set()
                    
                    for q in questions_data:
                        q_id = q.get("id")
                        if q_id in existing_ids:
                            quest = Question.query.get(q_id)
                            quest.question_text = q.get("question_text")
                            quest.question_description = q.get("question_description")
                            quest.question_type = q.get("question_type")
                            quest.order = q.get("order")
                            quest.is_required = q.get("is_required")
                            quest.options = q.get("options")
                            incoming_ids.add(q_id)
                        else:
                            new_q = Question(
                                form_id=form.id,
                                question_text=q.get("question_text"),
                                question_description=q.get("question_description"),
                                question_type=q.get("question_type"),
                                is_required=q.get("is_required"),
                                order=q.get("order"),
                                options=q.get("options")
                            )
                            db.session.add(new_q)
                    
                    to_delete = existing_ids - incoming_ids
                    if to_delete:
                        Question.query.filter(Question.id.in_(to_delete)).delete(synchronize_session=False)

                msg = "Form updated successfully."

            db.session.commit()
            
            if request.is_json:
                return jsonify({"success": True, "message": msg})
            
            flash(msg, "success")
            return redirect(url_for("forms.list_forms"))

        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({"success": False, "error": str(e)}), 400
            
            flash(str(e), "error")

    existing_types = get_existing_form_types()
    return render_template("forms/edit_forms.html", form=form, existing_types=existing_types)

@bp.route("/<form_id>", methods=["GET"])
@login_required
@form_access_required
def get_form(form_id):
    form = Form.query.options(joinedload(Form.questions)).get_or_404(form_id)
    if request.is_json:
        return jsonify({
            "success": True, 
            "form": {
                "id": form.id, 
                "name": form.name, 
                "version": form.version, 
                "questions": [
                    {
                        "id": q.id, 
                        "question_text": q.question_text, 
                        "options": q.options, 
                        "order": q.order, 
                        "question_type": q.question_type, 
                        "is_required": q.is_required
                    } 
                    for q in sorted(form.questions, key=lambda x: x.order)
                ]
            }
        })
    return redirect(url_for("forms.edit_form", form_id=form_id))

@bp.route("/<form_id>/delete", methods=["POST", "DELETE"])
@login_required
@form_access_required
def delete_form(form_id):
    """Marks a form as inactive (Soft Delete)."""
    form = Form.query.get_or_404(form_id)
    form.is_active = False
    db.session.commit()
    
    if request.is_json:
        return jsonify({"success": True})
    
    return redirect(url_for("forms.list_forms"))

@bp.route("/<form_id>/activate", methods=["POST"])
@login_required
@form_access_required
def activate_form(form_id):
    """
    Activates a previously deactivated form.
    Ensures only one 'active' version exists for forms with the same name.
    """
    form = Form.query.get_or_404(form_id)
    
    # Check for another active form with the same name
    existing_active = Form.query.filter(
        Form.name == form.name,
        Form.is_active,
        Form.id != form.id
    ).first()
    
    if existing_active:
        error_msg = f"Cannot activate. '{form.name}' already has an active version (v{existing_active.version})."
        if request.is_json:
            return jsonify({"success": False, "error": error_msg}), 400
        
        flash(error_msg, "error")
        return redirect(url_for("forms.list_forms"))
    
    try:
        form.is_active = True
        form.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        success_msg = f"Form '{form.name}' (v{form.version}) has been activated."
        if request.is_json:
            return jsonify({"success": True, "message": success_msg})
        
        flash(success_msg, "success")
        return redirect(url_for("forms.list_forms"))
        
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({"success": False, "error": str(e)}), 500
        
        flash(str(e), "error")
        return redirect(url_for("forms.list_forms"))