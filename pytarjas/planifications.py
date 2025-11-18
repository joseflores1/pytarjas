# pytarjas/planifications.py
"""
Planifications blueprint for managing work planifications and documents.

This blueprint handles the complete workflow of planifications:
1. Planners create planifications through HTML forms (manual data entry)
2. System auto-generates Documents directly from the planification data
3. Workers access their assigned documents through the tasks interface
4. Planners review completed work

SIMPLIFIED: Record class has been removed - Documents now contain data directly.

REASONING BEHIND THE CODE:
- Planifications are work orders/schedules created by Planners
- Each planification can have multiple Documents (work items)
- Documents contain task data (record_data) and are filled by Workers during field work
- This is the entry point for all field work - without planifications, workers have nothing to do

ACCESS CONTROL:
- Planners: Can create, view, edit, and delete planifications
- Admins: Full access to all planifications
- Workers: NO ACCESS (they do not need to know) 
- Clients: NO ACCESS (this is internal operational data)

DUAL RESPONSE FORMAT:
- Supports both HTML (browser) and JSON (PWA/API) responses
- Same endpoints serve both traditional web interface and Progressive Web App
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, g, abort, current_app #noqa
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
import uuid
from functools import wraps

# Import database and models
from pytarjas.models.user_models import db, User
from pytarjas.models.docs_models import Planification, Document, Form, Question #noqa

# Import authentication decorators
from pytarjas.auth import login_required

# Import helper functions
from pytarjas.helper import wants_json

# Create blueprint with URL prefix /planifications
# This organizes all planification-related routes under /planifications/*
bp = Blueprint("planifications", __name__, url_prefix="/planifications")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def check_planification_access(planification_id: str) -> Planification:
    """
    Check if current user has access to a planification and return it.
    
    REASONING:
    - Centralized access control logic for all planification operations
    - Different rules for different roles (admin, planner, worker)
    - Returns the planification if access is granted, aborts otherwise
    
    ACCESS RULES:
    - Admins: Can access ALL planifications
    - Planners: Can access planifications they created OR all if viewing
    - Workers: NO ACCESS 
    - Clients: NO ACCESS (will be blocked by decorator before reaching here)
    
    Args:
        planification_id: UUID of the planification to check
        
    Returns:
        Planification: The planification object if access is granted
        
    Raises:
        404: If planification doesn't exist
        403: If user doesn't have access
    """
    # Fetch planification with eager loading of relationships
    # joinedload prevents N+1 query problems by loading related data in one query
    # UPDATED: records â†’ documents (Record class removed)
    planification = Planification.query.options(
        joinedload(Planification.planner),
        joinedload(Planification.form),
        joinedload(Planification.documents)  # Load documents instead of records
    ).get_or_404(planification_id)
    
    # Role-based access control
    if g.user.role == "admin":
        # Admins have full access to everything
        return planification
    
    elif g.user.role == "planner" and g.user.id == planification.planner_id:
        # Planners can access any planification (for coordination purposes)
        # In a stricter system, you might limit this to planifications they created
        return planification
    
    else:
        # Clients and any other roles are denied
        abort(403)


# ============================================================================
# DECORATOR: planification_access_required
# ============================================================================

def planification_access_required(view):
    """
    Decorator to require planification access permissions.
    
    REASONING:
    - Planifications are internal operational data, not for clients
    - Workers can view (read-only) to understand their work context
    - Planners and admins can create/modify planifications
    
    MUST be used AFTER @login_required decorator.
    
    Usage:
        @bp.route('/list')
        @login_required
        @planification_access_required
        def list_planifications():
            return jsonify(...)
    
    Behavior:
    - Blocks 'client' role completely
    - Allows admin, planner, worker roles
    """
    
    @wraps(view)
    def wrapped_view(**kwargs):
        # Client role is not allowed to access planifications at all
        if g.user.role == "client" or g.user.role == "worker":
            # Return appropriate error format based on request type
            if wants_json():
                return jsonify({
                    "success": False,
                    "error": "Access denied. Clients cannot access planifications."
                }), 403
            else:
                # HTML error page using Flask's abort
                abort(403)
        
        # User has permission - proceed with the view
        return view(**kwargs)
    
    return wrapped_view


# ============================================================================
# ROUTE: List all planifications
# ============================================================================

@bp.route("/", methods=["GET"])
@login_required
@planification_access_required
def list_planifications():
    """
    List all planifications with role-based filtering.
    
    REASONING:
    - Provides an overview of all work planifications in the system
    - Supports filtering to help users find specific planifications
    - Role-based visibility (workers see all, planners see all, admins see all)
    - Shows key metrics like total records and completion status
    
    DUAL RESPONSE ENDPOINT: Returns JSON or HTML based on request headers.
    
    Query Parameters:
    - status: Filter by status (uploaded, processing, completed, error, all)
    - planner_id: Filter by planner who created it (admin/planner only)
    - client_name: Search by client name (partial match)
    - form_type: Filter by form type
    - limit: Max results to return (default: 50, max: 100)
    - offset: Pagination offset (default: 0)
    
    Examples:
    - GET /planifications - All planifications
    - GET /planifications?status=completed - Only completed ones
    - GET /planifications?client_name=ACME - Search by client
    - GET /planifications?form_type=consolidado - Filter by form type
    
    JSON Success Response (200):
    {
        "success": true,
        "planifications": [
            {
                "id": "uuid-here",
                "client_name": "ACME Corp",
                "form_name": "Formulario Consolidado",
                "form_type": "consolidado",
                "status": "completed",
                "total_documents": 25,
                "completed_documents": 23,
                "planner": {
                    "id": "planner-uuid",
                    "username": "maria_planner"
                },
                "created_at": "2025-10-20T08:00:00Z",
                "updated_at": "2025-10-22T16:30:00Z"
            }
        ],
        "total": 1,
        "limit": 50,
        "offset": 0,
        "filters": {
            "status": null,
            "client_name": null
        }
    }
    
    HTML Response:
        Renders 'planifications/list_planifications.html' template
    """
    # Get query parameters with defaults and validation
    status_filter = request.args.get('status', 'all')
    planner_id_filter = request.args.get('planner_id')
    form_id_filter=request.args.get("form_id")
    client_name_search = request.args.get('client_name', '').strip()
    form_type_filter = request.args.get('form_type')
    limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 items
    offset = int(request.args.get('offset', 0))
    
    # Build query with eager loading for better performance
    # joinedload prevents N+1 queries by fetching related data in one SQL query
    # UPDATED: records â†’ documents (Record class removed)
    query = Planification.query.options(
        joinedload(Planification.planner),
        joinedload(Planification.form),
        joinedload(Planification.documents)  # Load documents instead of records
    )
    
    # Apply filters based on query parameters
    
    # Status filter
    if status_filter != 'all':
        query = query.filter(Planification.status == status_filter)
    
    # Planner filter (admin/planner only)
    if planner_id_filter and g.user.role in ['admin', 'planner']:
        query = query.filter(Planification.planner_id == planner_id_filter)
    
    # Client name search (case-insensitive partial match)
    # ilike = SQL case-insensitive LIKE operator
    if client_name_search:
        query = query.filter(Planification.client_name.ilike(f'%{client_name_search}%'))
    
    # Form type filter
    if form_type_filter:
        query = query.join(Form).filter(Form.form_type == form_type_filter)
    
    if form_id_filter:
        query = query.filter(Planification.form_id == form_id_filter)

    # Get total count BEFORE pagination (for "showing X of Y results")
    total = query.count()
    
    # Apply pagination and execute query
    # Order by creation date (newest first)
    planifications = query.order_by(
        Planification.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    # Serialize planifications to dictionary format
    # This creates a structure that works for both JSON responses and HTML templates
    planifications_data = []
    for plan in planifications:
        # Count completed documents for progress tracking
        # UPDATED: Iterate over plan.documents directly (no longer through records)
        completed_docs = sum(
            1 for doc in plan.documents 
            if doc.status == 'completed'
        )
        
        plan_dict = {
            "id": plan.id,
            "client_name": plan.client_name,
            "form_name": plan.form.name,
            "form_type": plan.form.form_type,
            "status": plan.status,
            "total_documents": plan.total_documents,  # UPDATED: total_records â†’ total_documents
            "completed_documents": completed_docs,
            "planner": {
                "id": plan.planner.id,
                "username": plan.planner.username
            },
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
            # Include the full object for HTML templates (for easier access to nested data)
            "_planification": plan
        }
        planifications_data.append(plan_dict)
    
    # DUAL RESPONSE: Check what format the client wants
    if wants_json():
        # JSON Response - for API clients, AJAX, PWA service worker
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
    
    # HTML Response - for browser clicks
    # Get all planners for filter dropdown (admin/planner only)
    planners = []
    if g.user.role in ['admin', 'planner']:
        planners = User.query.filter_by(role='planner').all()
    
    # Get all form types for filter dropdown
    form_types = db.session.query(Form.form_type).distinct().all()
    form_types = [ft[0] for ft in form_types if ft[0]]  # Extract strings from tuples
    
    return render_template(
        "planifications/list_planifications.html",
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
# ROUTE: Get single planification with details
# ============================================================================

@bp.route("/<planification_id>", methods=["GET"])
@login_required
@planification_access_required
def get_planification(planification_id):
    """
    Get detailed information about a specific planification.
    
    REASONING:
    - Shows complete planification structure including all documents
    - Displays form template being used
    - Shows progress (how many documents completed)
    - Workers use this to understand their assignment context (if needed)
    - Planners use this to review and manage planifications
    
    UPDATED: Now directly shows documents (Record class removed for simplicity)
    
    DUAL RESPONSE ENDPOINT: Returns JSON or HTML based on request headers.
    
    Returns complete planification information including:
    - Planification metadata (client, status, dates)
    - Associated form structure
    - All documents with their status and worker assignments
    - Progress metrics
    
    GET /planifications/<planification_id>
    
    JSON Success Response (200):
    {
        "success": true,
        "planification": {
            "id": "plan-uuid",
            "client_name": "ACME Corp",
            "status": "completed",
            "total_documents": 10,
            "form": {
                "id": "form-uuid",
                "name": "Formulario Consolidado",
                "form_type": "consolidado",
                "questions": [...]
            },
            "documents": [
                {
                    "id": "doc-uuid-1",
                    "record_data": {"container_number": "ABCD123", ...},
                    "status": "completed",
                    "worker": {...},
                    "started_at": "2025-10-22T08:00:00Z",
                    "completed_at": "2025-10-22T10:30:00Z"
                }
            ],
            "planner": {...},
            "progress": {
                "total": 10,
                "pending": 2,
                "in_progress": 3,
                "completed": 5
            },
            "created_at": "2025-10-20T08:00:00Z"
        }
    }
    
    HTML Response:
        Renders 'planifications/view_planification.html' template
    """
    # Check access and get planification
    # This will automatically enforce role-based access control
    planification = check_planification_access(planification_id)
    
    # Calculate progress metrics
    # Count documents by status for progress tracking
    # UPDATED: Direct iteration over documents (Record class removed)
    progress = {
        "total": planification.total_documents,
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
        "reviewed": 0,
        "approved": 0
    }
    
    # UPDATED: Iterate directly over planification.documents
    for document in planification.documents:
        status = document.status
        if status in progress:
            progress[status] += 1
        else:
            progress["pending"] += 1  # Default to pending if unknown status
    
    # Serialize documents with their data
    # UPDATED: Changed from records_data to documents_data for clarity
    documents_data = []
    for document in planification.documents:
        doc_dict = {
            "id": document.id,
            "record_data": document.record_data,  # Task-specific data stored in document
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
    
    # DUAL RESPONSE: Check what format the client wants
    if wants_json():
        # JSON Response - includes full nested structure
        return jsonify({
            "success": True,
            "planification": {
                "id": planification.id,
                "client_name": planification.client_name,
                "status": planification.status,
                "total_documents": planification.total_documents,  # UPDATED: total_records → total_documents
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
                },
                "documents": documents_data,  # UPDATED: records → documents
                "planner": {
                    "id": planification.planner.id,
                    "username": planification.planner.username,
                    "email": planification.planner.email
                },
                "progress": progress,
                "created_at": planification.created_at.isoformat() if planification.created_at else None,
                "updated_at": planification.updated_at.isoformat() if planification.updated_at else None
            }
        }), 200
    
    # HTML Response - render detailed view template
    return render_template(
        "planifications/view_planification.html",
        planification=planification,
        documents=documents_data,  # UPDATED: Pass documents instead of records
        progress=progress,
        user=g.user
    )


# ============================================================================
# ROUTE: Create new planification (GET = show form, POST = submit)
# ============================================================================

@bp.route("/create", methods=["GET", "POST"])
@login_required
@planification_access_required
def create_planification():
    """
    Create a new planification through HTML form or JSON API.
    
    REASONING:
    - Planners create planifications to define work for workers
    - Each planification specifies WHAT form to use and WHAT data to collect
    - Documents are created directly from the planification data (one per work item)
    - Each document represents a task for a worker to complete in the field
    
    SIMPLIFIED: Documents are now created directly (Record class removed)
    
    ACCESS CONTROL:
    - Only planners and admins can create planifications
    - Workers cannot create (they only work on assigned documents)
    
    GET: Show planification creation form
    POST: Create the planification and generate documents
    
    Form/JSON Fields (required):
    - client_name: Name of the client this work is for
    - form_id: UUID of the form template to use
    - records: List of record data dictionaries (the work items - name kept for API compatibility)
    
    Form/JSON Fields (optional):
    - status: Initial status (default: "uploaded")
    
    Example JSON Request:
    POST /planifications/create
    {
        "client_name": "ACME Corp",
        "form_id": "form-uuid-here",
        "records": [
            {
                "container_number": "ABCD1234567",
                "ship_name": "MSC Luna",
                "booking_number": "BK20250001"
            },
            {
                "container_number": "EFGH9876543",
                "ship_name": "MSC Luna",
                "booking_number": "BK20250001"
            }
        ]
    }
    
    JSON Success Response (201):
    {
        "success": true,
        "message": "Planification created successfully with 2 documents.",
        "planification": {
            "id": "plan-uuid",
            "client_name": "ACME Corp",
            "total_documents": 2,
            "status": "completed",
            "created_at": "2025-10-22T14:30:00Z"
        }
    }
    
    JSON Error Response (400):
    {
        "success": false,
        "error": "Form not found."
    }
    """
    # Permission check: Only planners and admins can CREATE planifications
    # Workers can view, but not create
    if g.user.role not in ['planner', 'admin']:
        error_msg = "Access denied. Only planners and admins can create planifications."
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 403
        else:
            flash(error_msg, "error")
            return redirect(url_for("planifications.list_planifications"))
    
    # GET request: Show the creation form
    if request.method == "GET":
        if wants_json():
            # For JSON clients, return available forms for selection
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
            # HTML: Show form with available forms for selection
            active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
            return render_template(
                "planifications/create_planification.html",
                forms=active_forms,
                user=g.user
            )
    
    # POST request: Create the planification
    error = None
    
    # Extract data from request (JSON or form data)
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
        
        # For HTML forms, records are submitted differently
        # We'll collect all record fields from form arrays
        # Format: record_0_field, record_1_field, etc.
        records_data = []
        record_index = 0
        
        # Keep collecting records until we don't find the next index
        while True:
            # Check if this record exists by looking for a required field
            # We'll use a generic "data" field that planners can fill
            record_field_key = f"record_{record_index}_data"
            
            if record_field_key not in request.form:
                break  # No more records
            
            # Build record data from form fields
            # This collects all fields starting with "record_X_"
            record_data = {}
            prefix = f"record_{record_index}_"
            
            for key in request.form.keys():
                if key.startswith(prefix):
                    field_name = key[len(prefix):]  # Remove prefix
                    record_data[field_name] = request.form.get(key)
            
            if record_data:  # Only add if there's data
                records_data.append(record_data)
            
            record_index += 1
    
    # Validation
    if not client_name:
        error = "Client name is required."
    elif not form_id:
        error = "Form selection is required."
    elif not records_data or len(records_data) == 0:
        error = "At least one record is required."
    else:
        # Verify form exists and is active
        form = Form.query.filter_by(id=form_id, is_active=True).first()
        if not form:
            error = "Form not found or inactive."
    
    # If validation passed, create the planification
    if error is None:
        try:
            # Create the Planification object
            planification = Planification(
                id=str(uuid.uuid4()),
                planner_id=g.user.id,
                form_id=form_id,
                client_name=client_name,
                status=status,
                total_documents=len(records_data),  # UPDATED: total_records → total_documents
                file_path="",  # No file upload in this version
                file_name="",  # Manual entry via form
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(planification)
            
            # Create Documents directly from the submitted data
            # SIMPLIFIED: No longer creating Records first - Documents contain data directly
            # Each document represents one work item for a worker to complete
            created_documents = []
            for record_data in records_data:
                document = Document(
                    id=str(uuid.uuid4()),
                    planification_id=planification.id,  # Link to batch planification
                    form_id=form_id,  # Direct reference to form template
                    record_data=record_data,  # JSON field stores flexible task data
                    created_by_id=g.user.id,
                    worker_id=None,  # Not assigned yet - will be assigned manually or automatically
                    status="pending",  # Waiting to be assigned and filled
                    responses={},  # Empty responses to start - worker will fill these
                    photos=[],  # No photos yet - worker will add during field work
                    is_synced=True,  # Starts as synced (no offline changes yet)
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(document)
                created_documents.append(document)
            
            # Update planification counters and status
            planification.total_documents = len(records_data)  # Track how many documents created
            planification.status = "completed"  # All documents created successfully
            planification.updated_at = datetime.now(timezone.utc)
            
            # Commit all changes to database
            # This commits the planification + all documents in one transaction
            db.session.commit()
            
            success_message = (
                f"Planification created successfully with {len(records_data)} documents."
            )
            
            # Return appropriate response
            if wants_json():
                return jsonify({
                    "success": True,
                    "message": success_message,
                    "planification": {
                        "id": planification.id,
                        "client_name": planification.client_name,
                        "total_documents": planification.total_documents,  # UPDATED: total_records → total_documents
                        "status": planification.status,
                        "created_at": planification.created_at.isoformat()
                    }
                }), 201
            else:
                flash(success_message, "success")
                return redirect(url_for("planifications.get_planification", planification_id=planification.id))
        
        except Exception as e:
            db.session.rollback()
            error = f"An error occurred while creating planification: {str(e)}"
    
    # Handle errors
    if wants_json():
        return jsonify({
            "success": False,
            "error": error
        }), 400
    else:
        flash(error, "error")
        # Re-render form with error message
        active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
        return render_template(
            "planifications/create_planification.html",
            forms=active_forms,
            user=g.user,
            error=error
        )


# ============================================================================
# ROUTE: Delete planification (soft delete)
# ============================================================================

@bp.route("/<planification_id>/delete", methods=["POST", "DELETE"])
@login_required
@planification_access_required
def delete_planification(planification_id):
    """
    Delete a planification (changes status to mark as deleted).
    
    REASONING:
    - We use status change instead of hard delete to preserve data integrity
    - Hard deletion would cascade to records and documents (losing work history)
    - This approach allows "undoing" deletions if needed
    - Historical data remains intact for auditing
    
    ACCESS CONTROL:
    - Only planners and admins can delete planifications
    - Workers cannot delete (read-only access)
    
    POST or DELETE: Mark planification as deleted
    
    JSON Success Response (200):
    {
        "success": true,
        "message": "Planification deleted successfully."
    }
    
    JSON Error Response (403):
    {
        "success": false,
        "error": "Access denied. Only planners and admins can delete planifications."
    }
    
    Security Considerations:
    - Check if there are completed documents (may want to prevent deletion)
    - Only planner who created it or admin can delete
    """
    # Permission check: Only planners and admins can DELETE
    if g.user.role not in ['planner', 'admin']:
        error_msg = "Access denied. Only planners and admins can delete planifications."
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 403
        else:
            flash(error_msg, "error")
            return redirect(url_for("planifications.list_planifications"))
    
    # Check access and get planification
    planification = check_planification_access(planification_id)
    
    # Additional permission: Planners can only delete their own planifications
    # Admins can delete any planification
    if g.user.role == 'planner' and planification.planner_id != g.user.id:
        error_msg = "Access denied. You can only delete planifications you created."
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 403
        else:
            flash(error_msg, "error")
            return redirect(url_for("planifications.list_planifications"))
    
    # OPTIONAL: Check if there are completed documents
    # You might want to prevent deletion if work has been done
    # completed_count = sum(
    #     1 for doc in planification.documents
    #     if doc.status == 'completed'
    # )
    # if completed_count > 0:
    #     error_msg = f"Cannot delete planification with {completed_count} completed documents."
    #     ...
    
    try:
        # "Soft delete" by changing status
        # This preserves all related records and documents
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
            return redirect(url_for("planifications.list_planifications"))
    
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
            return redirect(url_for("planifications.list_planifications"))


# ============================================================================
# ROUTE: Update planification status
# ============================================================================

@bp.route("/<planification_id>/status", methods=["PUT", "PATCH"])
@login_required
@planification_access_required
def update_planification_status(planification_id):
    """
    Update planification status.
    
    REASONING:
    - Allows changing status without modifying other fields
    - Useful for workflow state transitions
    - Lightweight endpoint for status updates only
    
    ACCESS CONTROL:
    - Only planners and admins can update status
    
    JSON-ONLY ENDPOINT (no HTML form)
    
    JSON Request:
    {
        "status": "completed"
    }
    
    Valid statuses:
    - uploaded: Initial state
    - processing: System is processing the planification
    - completed: All records and documents created
    - error: Something went wrong
    - deleted: Soft deleted
    
    JSON Success Response (200):
    {
        "success": true,
        "message": "Status updated to 'completed'.",
        "planification": {
            "id": "uuid",
            "status": "completed",
            "updated_at": "2025-10-22T15:00:00Z"
        }
    }
    """
    # Permission check
    if g.user.role not in ['planner', 'admin']:
        return jsonify({
            "success": False,
            "error": "Access denied. Only planners and admins can update status."
        }), 403
    
    # Must be JSON request
    if not wants_json():
        return jsonify({
            "success": False,
            "error": "This endpoint only accepts JSON requests."
        }), 400
    
    # Check access and get planification
    planification = check_planification_access(planification_id)
    
    # Get new status from request
    data = request.get_json()
    new_status = data.get("status")
    
    # Validate status
    valid_statuses = ["uploaded", "processing", "completed", "error", "deleted"]
    if not new_status or new_status not in valid_statuses:
        return jsonify({
            "success": False,
            "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        }), 400
    
    try:
        # Update status
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