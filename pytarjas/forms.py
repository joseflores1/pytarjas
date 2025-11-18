# pytarjas/forms.py
"""
Forms blueprint for managing Form templates and Questions.

This blueprint allows Admins, Planners, and Workers to create and manage
form templates that will be used for tarja documents during field work.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, g
from sqlalchemy import insert
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
import uuid
import json
from pytarjas.models.user_models import db
from pytarjas.models.docs_models import Form, Question
from pytarjas.auth import login_required, form_access_required

# Create blueprint with URL prefix /forms
bp = Blueprint("forms", __name__, url_prefix="/forms")

# ============================================================================
# ROUTE: List all forms
# ============================================================================
@bp.route("/")
@login_required
@form_access_required
def list_forms():
    # Get filter parameters from query string
    form_type_filter = request.args.get("form_type")
    is_active_filter = request.args.get("is_active")
    
    # Apply form_type filter if provided
    if form_type_filter:
        forms = Form.query.filter_by(form_type=form_type_filter).order_by(Form.created_at.desc()).all()
    # Apply is_active filter if provided
    elif is_active_filter and is_active_filter.lower() == "true":
        forms = Form.query.filter_by(is_active=is_active_filter).order_by(Form.created_at.desc()).all()
    else:
        forms = Form.query.all()
    
    if request.is_json:
        return jsonify({
            "success": True,
            "forms": [
                {
                    "id": form.id,
                    "name": form.name,
                    "description": form.description,
                    "form_type": form.form_type,
                    "is_active": form.is_active,
                    "created_at": form.created_at.isoformat() if form.created_at else None,
                    "updated_at": form.updated_at.isoformat() if form.updated_at else None,
                    "question_count": len(form.questions)
                }
                for form in forms
            ],
            "count": len(forms),
            "filters": {
                "form_type": form_type_filter,
                "is_active": is_active_filter
            }
        }), 200
    
    return render_template(
        "forms/list_forms.html",
        forms=forms,
        form_type_filter=form_type_filter,
        is_active_filter=is_active_filter
    )


# ============================================================================
# ROUTE: Get single form with all questions
# ============================================================================
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
                "description": form.description,
                "form_type": form.form_type,
                "is_active": form.is_active,
                "created_at": form.created_at.isoformat() if form.created_at else None,
                "updated_at": form.updated_at.isoformat() if form.updated_at else None,
                "questions": [
                    {
                        "id": q.id,
                        "question_text": q.question_text,
                        "question_type": q.question_type,
                        "is_required": q.is_required,
                        "order": q.order,
                        "options": q.options,
                        "created_at": q.created_at.isoformat() if q.created_at else None
                    }
                    for q in sorted(form.questions, key=lambda x: x.order)
                ]
            }
        }), 200
    else:
        return redirect(url_for("forms.edit_form", form_id=form_id))


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
                # FIX: Parse JSON string for options
                options_str = request.form.get(f"question_options_{q_id}")
                options_dict = None
                if options_str and options_str.strip():
                    try:
                        options_dict = json.loads(options_str)
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON options for question {q_id}")
                        options_dict = None

                question_data = {
                    "question_text": request.form.get(f"question_text_{q_id}"),
                    "question_type": request.form.get(f"question_type_{q_id}"),
                    "order": int(request.form.get(f"question_order_{q_id}", 0)),
                    "is_required": request.form.get(f"question_required_{q_id}") == "true",
                    "options": options_dict
                }
                questions_data.append(question_data)
        
        error = None
        
        if not name:
            error = "Form name is required."
        else:
            existing_form = Form.query.filter_by(name=name).first()
            if existing_form:
                error = f"Form name '{name}' is already in use."
        
        valid_question_types = ["text", "number", "photo", "date", "datetime", "boolean", "select", "textarea", "file"]
        if not error and questions_data:
            for idx, q in enumerate(questions_data):
                q_type = q.get("question_type")
                if q_type and q_type not in valid_question_types:
                    error = f"Invalid question type '{q_type}'."
                    break
        
        if error is None:
            try:
                new_form = Form(
                    name=name,
                    description=description,
                    form_type=form_type,
                    is_active=True,
                    created_by_id=g.user.id
                )
                
                db.session.add(new_form)
                db.session.flush()
                
                questions_to_insert = []
                for q_data in questions_data:
                    question_dict = {
                        "id": str(uuid.uuid4()),
                        "form_id": new_form.id,
                        "question_text": q_data.get("question_text", ""),
                        "question_type": q_data.get("question_type", "text"),
                        "is_required": q_data.get("is_required", True),
                        "order": q_data.get("order", 0),
                        "options": q_data.get("options"),
                        "created_at": datetime.now(timezone.utc)
                    }
                    questions_to_insert.append(question_dict)
                
                if questions_to_insert:
                    db.session.execute(
                        insert(Question),
                        questions_to_insert
                    )
                
                db.session.commit()
                
                success_message = f"Form '{name}' created successfully."
                
                if request.is_json:
                    return jsonify({
                        "success": True,
                        "message": success_message,
                        "form": {
                            "id": new_form.id,
                            "name": new_form.name,
                            "description": new_form.description,
                            "form_type": new_form.form_type,
                            "is_active": new_form.is_active,
                            "created_at": new_form.created_at.isoformat(),
                            "question_count": len(questions_data)
                        }
                    }), 201
                else:
                    flash(success_message, "success")
                    return redirect(url_for("forms.list_forms"))
                    
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred: {str(e)}"
        
        if request.is_json:
            return jsonify({"success": False, "error": error}), 400
        else:
            flash(error, "error")
    
    return render_template("forms/create_form.html")


# ============================================================================
# ROUTE: Edit existing form
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
            is_active = data.get("is_active", form.is_active)
            questions_data = data.get("questions")
        else:
            name = request.form.get("name", form.name)
            description = request.form.get("description", form.description)
            form_type = request.form.get("form_type", form.form_type)
            is_active = request.form.get("is_active", "true").lower() == "true"
            
            # IMPLEMENTED: Parse questions from HTML form for updates
            questions_data = []
            question_ids = request.form.getlist("question_ids[]")
            
            for q_id in question_ids:
                # FIX: Parse JSON string for options
                options_str = request.form.get(f"question_options_{q_id}")
                options_dict = None
                if options_str and options_str.strip():
                    try:
                        options_dict = json.loads(options_str)
                    except json.JSONDecodeError:
                        options_dict = None

                q_data = {
                    "id": q_id, # ID is passed for existing/new questions
                    "question_text": request.form.get(f"question_text_{q_id}"),
                    "question_type": request.form.get(f"question_type_{q_id}"),
                    "order": int(request.form.get(f"question_order_{q_id}", 0)),
                    "is_required": request.form.get(f"question_required_{q_id}") == "true",
                    "options": options_dict
                }
                questions_data.append(q_data)
        
        error = None
        changes = []
        
        if name != form.name:
            if not name:
                error = "Form name cannot be empty."
            else:
                existing_form = Form.query.filter_by(name=name).first()
                if existing_form and existing_form.id != form.id:
                    error = f"Form name '{name}' is already in use."
                else:
                    changes.append("name")
        
        if not error:
            if description != form.description: 
                changes.append("description")
            if form_type != form.form_type: 
                changes.append("form_type")
            if is_active != form.is_active: 
                changes.append("is_active")
            if questions_data is not None: 
                changes.append("questions")
        
        if error is None:
            try:
                form.name = name
                form.description = description
                form.form_type = form_type
                form.is_active = is_active
                form.updated_at = datetime.now(timezone.utc)
                
                if questions_data is not None:
                    existing_q_ids = {q.id for q in form.questions}
                    updated_q_ids = set()
                    
                    for q_data in questions_data:
                        q_id = q_data.get("id")
                        
                        if q_id and q_id in existing_q_ids:
                            # UPDATE existing question
                            question = Question.query.get(q_id)
                            if question:
                                question.question_text = q_data.get("question_text", question.question_text)
                                question.question_type = q_data.get("question_type", question.question_type)
                                question.is_required = q_data.get("is_required", question.is_required)
                                question.order = q_data.get("order", question.order)
                                question.options = q_data.get("options", question.options)
                                question.updated_at = datetime.now(timezone.utc)
                                updated_q_ids.add(q_id)
                        else:
                            # CREATE new question (ignore the temp 'new_xxx' ID and let DB/Model handle UUID)
                            new_question = Question(
                                id=str(uuid.uuid4()),
                                form_id=form.id,
                                question_text=q_data.get("question_text", ""),
                                question_type=q_data.get("question_type", "text"),
                                is_required=q_data.get("is_required", True),
                                order=q_data.get("order", 0),
                                options=q_data.get("options")
                            )
                            db.session.add(new_question)
                    
                    # Optional: Delete questions not present in update
                    # for q in form.questions:
                    #     if q.id not in updated_q_ids:
                    #         db.session.delete(q)
                
                db.session.commit()
                
                message = f"Form '{name}' updated successfully."
                
                if request.is_json:
                    return jsonify({
                        "success": True,
                        "message": message,
                        "changes": changes,
                        "form": {
                            "id": form.id,
                            "name": form.name,
                            "updated_at": form.updated_at.isoformat()
                        }
                    }), 200
                else:
                    flash(message, "success" if changes else "info")
                    return redirect(url_for("forms.list_forms"))
                    
            except Exception as e:
                db.session.rollback()
                error = f"Error updating form: {str(e)}"
        
        if request.is_json:
            return jsonify({"success": False, "error": error}), 400
        else:
            flash(error, "error")
    
    if request.is_json:
        return jsonify({
            "success": True,
            "form": {
                "id": form.id,
                "name": form.name,
                "description": form.description,
                "form_type": form.form_type,
                "is_active": form.is_active,
                "questions": [
                    {
                        "id": q.id,
                        "question_text": q.question_text,
                        "question_type": q.question_type,
                        "is_required": q.is_required,
                        "order": q.order,
                        "options": q.options
                    }
                    for q in sorted(form.questions, key=lambda x: x.order)
                ]
            }
        }), 200
    else:
        return render_template("forms/edit_form.html", form=form)


# ============================================================================
# ROUTE: Delete form (soft delete)
# ============================================================================
@bp.route("/<form_id>/delete", methods=["POST", "DELETE"])
@login_required
@form_access_required
def delete_form(form_id):
    form = Form.query.get_or_404(form_id)
    
    try:
        form.is_active = False
        form.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        success_message = f"Form '{form.name}' deactivated successfully."
        
        if request.is_json:
            return jsonify({
                "success": True,
                "message": success_message
            }), 200
        else:
            flash(success_message, "success")
            return redirect(url_for("forms.list_forms"))
            
    except Exception as e:
        db.session.rollback()
        error_message = f"An error occurred: {str(e)}"
        
        if request.is_json:
            return jsonify({
                "success": False,
                "error": error_message
            }), 500
        else:
            flash(error_message, "error")
            return redirect(url_for("forms.list_forms"))


# ============================================================================
# ROUTE: Activate form
# ============================================================================
@bp.route("/<form_id>/activate", methods=["POST", "PUT"])
@login_required
@form_access_required
def activate_form(form_id):
    form = Form.query.get_or_404(form_id)
    
    try:
        form.is_active = True
        form.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        success_message = f"Form '{form.name}' activated successfully."
        
        if request.is_json:
            return jsonify({
                "success": True,
                "message": success_message
            }), 200
        else:
            flash(success_message, "success")
            return redirect(url_for("forms.list_forms"))
            
    except Exception as e:
        db.session.rollback()
        error_message = f"An error occurred: {str(e)}"
        
        if request.is_json:
            return jsonify({
                "success": False,
                "error": error_message
            }), 500
        else:
            flash(error_message, "error")
            return redirect(url_for("forms.list_forms"))