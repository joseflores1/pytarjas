# pytarjas/forms.py
"""
Forms blueprint for managing Form templates and Questions.

This blueprint allows Admins, Planners, and Workers to create and manage
form templates that will be used for tarja documents during field work.

Clients do NOT have access to these endpoints.

Supports both HTML and JSON API for hybrid web/PWA architecture:
- HTML: Traditional browser-based interface
- JSON API: For Progressive Web App and future mobile apps

REASONING BEHIND THE CODE:
- Forms are reusable templates that define what data workers collect in the field
- Each Form has multiple Questions that can be text, numbers, photos, dates, etc.
- Only non-Client users can manage forms because forms are internal operational tools
- Soft deletion (is_active flag) preserves historical data while hiding inactive forms
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from sqlalchemy import insert
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
import uuid
from pytarjas.models.user_models import db
from pytarjas.models.docs_models import Form, Question
from pytarjas.auth import login_required, form_access_required

# Create blueprint with URL prefix /forms
# This organizes all form-related routes under /forms/*
bp = Blueprint("forms", __name__, url_prefix="/forms")

# ============================================================================
# ROUTE: List all forms
# ============================================================================
@bp.route("/")
@login_required
@form_access_required
def list_forms():
    """
    List all forms in the system.
    
    REASONING:
    - Provides an overview of all available form templates
    - Supports filtering to help users find specific forms quickly
    - Shows both active and inactive forms (admins may want to reactivate old forms)
    
    Query Parameters:
    - form_type: Filter by type (consolidado, desconsolidado, seal_verification, etc.)
    - is_active: Filter by status (true/false) - defaults to showing all
    
    Examples:
    - GET /forms - All forms
    - GET /forms?form_type=consolidado - Only consolidado forms
    - GET /forms?is_active=true - Only active forms
    - GET /forms?form_type=consolidado&is_active=true - Active consolidado forms
    
    JSON Success Response (200):
    {
        "success": true,
        "forms": [
            {
                "id": "uuid-1",
                "name": "Formulario de Consolidado",
                "description": "Form for consolidation operations",
                "form_type": "consolidado",
                "is_active": true,
                "created_at": "2025-01-01T00:00:00Z",
                "question_count": 15
            }
        ],
        "count": 1,
        "filters": {
            "form_type": "consolidado",
            "is_active": true
        }
    }
    """
    # Get filter parameters from query string
    form_type_filter = request.args.get("form_type")
    is_active_filter = request.args.get("is_active")  # Will be string "true" or "false"
    
    # Apply form_type filter if provided
    if form_type_filter:
        forms = Form.query.filter_by(form_type=form_type_filter).order_by(Form.created_at.desc()).all()
    # Apply is_active filter if provided
    # Convert string "true"/"false" to boolean
    elif is_active_filter and is_active_filter.lower() == "true":
        forms = Form.query.filter_by(is_active=is_active_filter).order_by(Form.created_at.desc()).all()
    else:
        forms=Form.query.all()
    
    # Check if request expects JSON response
    if request.is_json:
        # JSON response for API clients (PWA, mobile apps)
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
                    "question_count": len(form.questions)  # Count related questions
                }
                for form in forms
            ],
            "count": len(forms),
            "filters": {
                "form_type": form_type_filter,
                "is_active": is_active_filter
            }
        }), 200
    
    # HTML response for browser clients
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
    """
    Get a single form by ID with all its questions.
    
    REASONING:
    - Workers need to see the complete form structure before using it
    - Planners need to review forms when assigning them to planifications
    - Uses eager loading (joinedload) to fetch questions in one query (performance optimization)
    
    GET /forms/<form_id>
    
    JSON Success Response (200):
    {
        "success": true,
        "form": {
            "id": "uuid-here",
            "name": "Formulario de Consolidado",
            "description": "Detailed description...",
            "form_type": "consolidado",
            "is_active": true,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-20T10:35:00Z",
            "questions": [
                {
                    "id": "q-uuid-1",
                    "question_text": "¿Número de contenedor?",
                    "question_type": "text",
                    "is_required": true,
                    "order": 1,
                    "options": {"maxlength": 50}
                }
            ]
        }
    }
    
    JSON Error Response (404):
    {
        "success": false,
        "error": "Form not found."
    }
    
    PERFORMANCE OPTIMIZATION:
    - Uses joinedload() to fetch form and questions in one SQL query
    - Without this, SQLAlchemy would make separate queries (N+1 problem)
    """
    # Query form with eager loading of questions (prevents N+1 query problem)
    # joinedload fetches the form and all related questions in a single SQL JOIN
    form = Form.query.options(joinedload(Form.questions)).get_or_404(form_id)
    
    # Check if request expects JSON response
    if request.is_json:
        # JSON response includes full form details with all questions
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
                        "options": q.options,  # JSON field with validation rules, etc.
                        "created_at": q.created_at.isoformat() if q.created_at else None
                    }
                    # Sort questions by order field for consistent display
                    for q in sorted(form.questions, key=lambda x: x.order)
                ]
            }
        }), 200
    else:
        # HTML clients get redirected to edit page (shows full form details)
        return redirect(url_for("forms.edit_form", form_id=form_id))


# ============================================================================
# ROUTE: Create new form
# ============================================================================
@bp.route("/create", methods=["GET", "POST"])
@login_required
@form_access_required
def create_form():
    """
    Create a new form template with questions.
    
    REASONING:
    - Forms are created once and reused many times for different planifications
    - Questions are created together with the form in a single transaction
    - Using db.session.bulk_save_objects() for performance when adding many questions
    
    GET: Display form creation interface (HTML only)
    POST: Process form creation request
    
    Accepts two content types:
    1. application/x-www-form-urlencoded (HTML forms)
    2. application/json (API/PWA requests)
    
    JSON Request Example:
    {
        "name": "Formulario de Consolidado 2025",
        "description": "Updated form for consolidation operations",
        "form_type": "consolidado",
        "questions": [
            {
                "question_text": "¿Número de contenedor?",
                "question_type": "text",
                "is_required": true,
                "order": 1,
                "options": {"maxlength": 50, "placeholder": "Ej: ABCD1234567"}
            },
            {
                "question_text": "¿Foto del sello?",
                "question_type": "photo",
                "is_required": true,
                "order": 2,
                "options": {"max_size_mb": 10}
            }
        ]
    }
    
    JSON Success Response (201):
    {
        "success": true,
        "message": "Form 'Formulario de Consolidado 2025' created successfully with 2 questions.",
        "form": {
            "id": "uuid-here",
            "name": "Formulario de Consolidado 2025",
            "form_type": "consolidado",
            "created_at": "2025-01-20T10:30:00Z",
            "question_count": 2
        }
    }
    
    JSON Error Response (400):
    {
        "success": false,
        "error": "Form name is already in use."
    }
    
    Validation:
    - Form name must be unique
    - Form name is required
    - Form type is optional but recommended
    - At least one question is recommended (but not required)
    - Question types must be valid (text, number, photo, date, boolean, select, textarea)
    """
    if request.method == "POST":
        # Extract data based on content type
        if request.is_json:
            # JSON request from API/PWA
            data = request.get_json()
            name = data.get("name")
            description = data.get("description")
            form_type = data.get("form_type")
            questions_data = data.get("questions", [])  # List of question objects
        else: 
            # In create_form() function, around line 303:
            if not request.is_json:
                name = request.form.get("name")
                description = request.form.get("description")
                form_type = request.form.get("form_type")
                
                # Parse questions from HTML form
                questions_data = []
                question_ids = request.form.getlist("question_ids[]")
                
                for q_id in question_ids:
                    question_data = {
                        "question_text": request.form.get(f"question_text_{q_id}"),
                        "question_type": request.form.get(f"question_type_{q_id}"),
                        "order": int(request.form.get(f"question_order_{q_id}", 0)),
                        "is_required": request.form.get(f"question_required_{q_id}") == "true",
                        "options": request.form.get(f"question_options_{q_id}") or None
                    }
                    questions_data.append(question_data)
        error = None
        
        # Validation: Form name is required
        if not name:
            error = "Form name is required."
        else:
            # Check if form name already exists (must be unique)
            existing_form = Form.query.filter_by(name=name).first()
            if existing_form:
                error = f"Form name '{name}' is already in use. Please choose a different name."
        
        # Validation: Question types must be valid
        valid_question_types = ["text", "number", "photo", "date", "datetime", "boolean", "select", "textarea"]
        if not error and questions_data:
            for idx, q in enumerate(questions_data):
                q_type = q.get("question_type")
                if q_type and q_type not in valid_question_types:
                    error = f"Invalid question type '{q_type}' in question #{idx + 1}. Valid types: {', '.join(valid_question_types)}"
                    break
        
        # If all validation passes, create the form
        if error is None:
            try:
                # Create Form object
                new_form = Form(
                    name=name,
                    description=description,
                    form_type=form_type,
                    is_active=True  # New forms are active by default
                )
                
                # Add form to session
                db.session.add(new_form)
                # Flush to get the form.id without committing
                # This allows us to reference new_form.id when creating questions
                db.session.flush()
                
                # Create Question dictionaries for bulk insert
                # PERFORMANCE OPTIMIZATION: Use SQLAlchemy 2.0 bulk insert
                # This is much faster than adding objects one by one
                # It generates a single INSERT statement with multiple rows
                # 
                # Note: We must explicitly generate UUIDs because the default lambda
                # in the model (default=lambda: str(uuid.uuid4())) doesn't work with bulk insert
                questions_to_insert = []
                for q_data in questions_data:
                    question_dict = {
                        "id": str(uuid.uuid4()),  # Explicitly generate UUID
                        "form_id": new_form.id,  # Link to the form we just created
                        "question_text": q_data.get("question_text", ""),
                        "question_type": q_data.get("question_type", "text"),
                        "is_required": q_data.get("is_required", True),
                        "order": q_data.get("order", 0),
                        "options": q_data.get("options"),  # JSON field for additional config
                        "created_at": datetime.now(timezone.utc)
                    }
                    questions_to_insert.append(question_dict)
                
                # Execute bulk insert using modern SQLAlchemy 2.0 approach
                # This replaces the legacy bulk_save_objects() method
                # See: https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html#orm-bulk-insert-statements
                if questions_to_insert:
                    db.session.execute(
                        insert(Question),
                        questions_to_insert
                    )
                
                # Commit the transaction (saves both form and questions)
                db.session.commit()
                
                # Success message
                question_count = len(questions_data)
                success_message = f"Form '{name}' created successfully"
                if question_count > 0:
                    success_message += f" with {question_count} question{'s' if question_count != 1 else ''}."
                else:
                    success_message += "."
                
                # Return appropriate response based on request type
                if request.is_json:
                    # JSON response for API clients
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
                            "question_count": question_count
                        }
                    }), 201
                else:
                    # HTML redirect for browser clients
                    flash(success_message, "success")
                    return redirect(url_for("forms.list_forms"))
                    
            except Exception as e:
                # Rollback on any error
                db.session.rollback()
                error = f"An error occurred while creating the form: {str(e)}"
        
        # Handle validation/creation errors
        if request.is_json:
            # Return JSON error for API clients
            return jsonify({
                "success": False,
                "error": error
            }), 400
        else:
            # Flash message for HTML clients
            flash(error, "error")
    
    # GET request: show form creation interface
    return render_template("forms/create_form.html")


# ============================================================================
# ROUTE: Edit existing form
# ============================================================================
@bp.route("/<form_id>/edit", methods=["GET", "PUT", "POST"])
@login_required
@form_access_required
def edit_form(form_id):
    """
    Edit an existing form and its questions.
    
    REASONING:
    - Forms may need updates (typos, additional questions, requirement changes)
    - Supports partial updates (only update provided fields)
    - Updates are careful not to affect existing Documents that use this form
    - When questions are modified, existing document responses remain valid
    
    GET: Display form edit interface (HTML only)
    PUT/POST: Update the form
    
    IMPORTANT CONSIDERATION:
    - Modifying a form affects NEW documents created from it
    - EXISTING documents (already in use) maintain their original structure
    - This is why we don't delete old questions, just mark forms as inactive
    
    JSON Request Example (Partial Update):
    {
        "description": "Updated description only",
        "is_active": false
    }
    
    JSON Request Example (Full Update with Questions):
    {
        "name": "Formulario de Consolidado v2",
        "description": "Updated form",
        "form_type": "consolidado",
        "is_active": true,
        "questions": [
            {
                "id": "existing-q-uuid",  // Update existing question
                "question_text": "Updated question text",
                "order": 1
            },
            {
                "question_text": "New question",  // Create new question (no id)
                "question_type": "text",
                "order": 2
            }
        ]
    }
    
    JSON Success Response (200):
    {
        "success": true,
        "message": "Form 'Formulario de Consolidado v2' updated successfully.",
        "changes": ["description", "questions"],
        "form": {
            "id": "uuid-here",
            "name": "Formulario de Consolidado v2",
            "updated_at": "2025-01-20T15:45:00Z"
        }
    }
    """
    # Query form with questions (eager loading for performance)
    form = Form.query.options(joinedload(Form.questions)).get_or_404(form_id)
    
    if request.method in ["POST", "PUT"]:
        # Extract data based on content type
        if request.is_json:
            data = request.get_json()
            # Support partial updates - use current values if not provided
            name = data.get("name", form.name)
            description = data.get("description", form.description)
            form_type = data.get("form_type", form.form_type)
            is_active = data.get("is_active", form.is_active)
            questions_data = data.get("questions")  # None if not provided
        else:
            # Form data from HTML
            name = request.form.get("name", form.name)
            description = request.form.get("description", form.description)
            form_type = request.form.get("form_type", form.form_type)
            is_active = request.form.get("is_active", "true").lower() == "true"
            questions_data = None  # TODO: Parse from HTML form
        
        error = None
        changes = []  # Track what changed for better response messages
        
        # Validation: Name (only if changed)
        if name != form.name:
            if not name:
                error = "Form name cannot be empty."
            else:
                # Check if new name is already taken by another form
                existing_form = Form.query.filter_by(name=name).first()
                if existing_form and existing_form.id != form.id:
                    error = f"Form name '{name}' is already in use by another form."
                else:
                    changes.append("name")
        
        # Track other changes
        if not error:
            if description != form.description:
                changes.append("description")
            if form_type != form.form_type:
                changes.append("form_type")
            if is_active != form.is_active:
                changes.append("is_active")
            if questions_data is not None:
                changes.append("questions")
        
        # If all validation passes, update the form
        if error is None:
            try:
                # Update form fields
                form.name = name
                form.description = description
                form.form_type = form_type
                form.is_active = is_active
                form.updated_at = datetime.now(timezone.utc)
                
                # Handle questions update if provided
                if questions_data is not None:
                    # Get existing question IDs
                    existing_q_ids = {q.id for q in form.questions}
                    updated_q_ids = set()
                    
                    # Process each question in the request
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
                            # CREATE new question
                            new_question = Question(
                                form_id=form.id,
                                question_text=q_data.get("question_text", ""),
                                question_type=q_data.get("question_type", "text"),
                                is_required=q_data.get("is_required", True),
                                order=q_data.get("order", 0),
                                options=q_data.get("options")
                            )
                            db.session.add(new_question)
                    
                    # DELETE questions not in the update (soft delete approach)
                    # NOTE: We don't actually delete to preserve data integrity
                    # Instead, you might want to mark them as deleted or just leave them
                    # For now, we'll leave orphaned questions (they won't appear in new forms)
                
                # Commit changes
                db.session.commit()
                
                # Build success message
                if not changes:
                    message = "No changes detected."
                else:
                    if len(changes) == 1:
                        change_text = changes[0]
                    elif len(changes) == 2:
                        change_text = f"{changes[0]} and {changes[1]}"
                    else:
                        change_text = ", ".join(changes[:-1]) + f", and {changes[-1]}"
                    message = f"Form '{name}' updated successfully. Changed: {change_text}."
                
                # Return appropriate response
                if request.is_json:
                    return jsonify({
                        "success": True,
                        "message": message,
                        "changes": changes,
                        "form": {
                            "id": form.id,
                            "name": form.name,
                            "description": form.description,
                            "form_type": form.form_type,
                            "is_active": form.is_active,
                            "updated_at": form.updated_at.isoformat()
                        }
                    }), 200
                else:
                    flash(message, "success" if changes else "info")
                    return redirect(url_for("forms.list_forms"))
                    
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred while updating the form: {str(e)}"
        
        # Handle errors
        if request.is_json:
            return jsonify({
                "success": False,
                "error": error
            }), 400
        else:
            flash(error, "error")
    
    # GET request: show edit interface
    if request.is_json:
        # Return current form data for JSON clients
        return jsonify({
            "success": True,
            "form": {
                "id": form.id,
                "name": form.name,
                "description": form.description,
                "form_type": form.form_type,
                "is_active": form.is_active,
                "created_at": form.created_at.isoformat(),
                "updated_at": form.updated_at.isoformat() if form.updated_at else None,
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
        # HTML edit form
        return render_template("forms/edit_form.html", form=form)


# ============================================================================
# ROUTE: Delete form (soft delete)
# ============================================================================
@bp.route("/<form_id>/delete", methods=["POST", "DELETE"])
@login_required
@form_access_required
def delete_form(form_id):
    """
    Delete a form (soft delete by setting is_active=False).
    
    REASONING:
    - We use SOFT DELETE to preserve data integrity
    - Hard deletion would break relationships with existing Planifications
    - Inactive forms are hidden from normal views but preserved in database
    - Historical documents maintain their structure even if form is "deleted"
    
    POST or DELETE: Mark form as inactive
    
    JSON Success Response (200):
    {
        "success": true,
        "message": "Form 'Formulario de Consolidado' deactivated successfully."
    }
    
    JSON Error Response (400):
    {
        "success": false,
        "error": "Cannot delete form that is in use by active planifications."
    }
    
    Security Considerations:
    - Check if form is in use by active planifications
    - Prevent deletion if it would cause data integrity issues
    """
    form = Form.query.get_or_404(form_id)
    
    # FUTURE ENHANCEMENT: Check if form is in use by active planifications
    # active_planifications = Planification.query.filter_by(
    #     form_id=form_id,
    #     status='active'
    # ).count()
    # if active_planifications > 0:
    #     error_message = "Cannot delete form that is in use by active planifications."
    #     ...
    
    # Soft delete: just mark as inactive
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
    """
    Activate a previously deactivated form.
    
    REASONING:
    - Forms might be temporarily disabled but needed again later
    - This allows reactivating without recreating the entire form
    - Useful for seasonal forms or forms that were disabled by mistake
    
    POST or PUT: Set is_active=True
    
    JSON Success Response (200):
    {
        "success": true,
        "message": "Form 'Formulario de Consolidado' activated successfully."
    }
    """
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