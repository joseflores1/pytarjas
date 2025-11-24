# pytarjas/admin.py
"""
Admin blueprint for user management.

Only users with 'admin' role can access these views.
Admins can create, list, edit, and delete users.

Supports both HTML and JSON API for hybrid web/PWA architecture:
- HTML: Traditional browser-based admin interface
- JSON API: For Progressive Web App and future mobile apps
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for, g, jsonify
from pytarjas.models.user_models import db, User, Admin, Worker, Planner, Client  # noqa
from pytarjas.auth import login_required, admin_required

# Create blueprint with URL prefix /admin
bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
@admin_required
def index():
    """
    Admin dashboard.
    
    Shows summary of users and quick links.
    Supports both HTML and JSON responses.
    
    GET /admin
    
    JSON Response (200):
    {
        "success": true,
        "stats": {
            "total": 25,
            "admin": 2,
            "worker": 15,
            "planner": 5,
            "client": 3
        }
    }
    """
    user_count = User.query.count()
    admin_count = User.query.filter_by(role="admin").count()
    worker_count = User.query.filter_by(role="worker").count()
    planner_count = User.query.filter_by(role="planner").count()
    client_count = User.query.filter_by(role="client").count()
    
    if request.is_json:
        return jsonify({
            "success": True,
            "stats": {
                "total": user_count,
                "admin": admin_count,
                "worker": worker_count,
                "planner": planner_count,
                "client": client_count
            }
        }), 200
    
    return render_template(
        "admin/index.html",
        user_count=user_count,
        admin_count=admin_count,
        worker_count=worker_count,
        planner_count=planner_count,
        client_count=client_count
    )


@bp.route("/users")
@login_required
@admin_required
def list_users():
    """
    List all users in the system.
    
    Supports both HTML and JSON responses.
    Allows filtering by role via query parameter.
    
    Query Parameters:
    - role: Filter by role (admin, worker, planner, client)
    
    Examples:
    - GET /admin/users - All users
    - GET /admin/users?role=worker - Only workers
    
    JSON Success Response (200):
    {
        "success": true,
        "users": [
            {
                "id": "uuid-1",
                "username": "admin",
                "email": "admin@example.com",
                "role": "admin",
                "created_at": "2025-01-01T00:00:00Z"
            }
        ],
        "count": 1,
        "filter": "worker"
    }
    """
    # Get role filter from query parameter
    role_filter = request.args.get("role")
    
    # Build query
    if role_filter:
        users = User.query.filter_by(role=role_filter).order_by(User.created_at.desc()).all()
    else:
        users = User.query.order_by(User.created_at.desc()).all()
    
    if request.is_json:
        # JSON response for API clients
        return jsonify({
            "success": True,
            "users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                    "login_at": user.login_at.isoformat() if user.login_at else None
                }
                for user in users
            ],
            "count": len(users),
            "filter": role_filter
        }), 200
    
    # HTML response for browser clients
    return render_template("admin/list_users.html", users=users, role_filter=role_filter)


@bp.route("/users/<user_id>", methods=["GET"])
@login_required
@admin_required
def get_user(user_id):
    """
    Get a single user by ID.
    
    This endpoint returns user details in JSON format.
    HTML clients should use edit_user instead.
    
    GET /admin/users/<user_id>
    
    JSON Success Response (200):
    {
        "success": true,
        "user": {
            "id": "uuid-here",
            "username": "john_worker",
            "email": "john@example.com",
            "role": "worker",
            "created_at": "2025-01-20T10:30:00Z",
            "updated_at": "2025-01-20T14:22:00Z",
            "login_at": "2025-01-21T08:15:00Z"
        }
    }
    
    JSON Error Response (404):
    {
        "success": false,
        "error": "User not found."
    }
    """
    user = User.query.get_or_404(user_id)
    
    if request.is_json:
        # JSON response
        return jsonify({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "login_at": user.login_at.isoformat() if user.login_at else None
        }
        }), 200
    else:
        # HTML clients should use the edit_user view instead
        return redirect(url_for("admin.edit_user", user_id=user_id))


@bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    """
    Create a new user.
    
    GET: Display user creation form (HTML only)
    POST: Process form and create user
    
    Accepts two content types:
    1. application/x-www-form-urlencoded (HTML forms)
    2. application/json (API/PWA requests)
    
    JSON Request Example:
    {
        "username": "john_worker",
        "email": "john@example.com",
        "password": "secure123",
        "password_confirm": "secure123",
        "role": "worker"
    }
    
    JSON Success Response (201):
    {
        "success": true,
        "message": "User 'john_worker' created successfully with role 'worker'.",
        "user": {
            "id": "uuid-here",
            "username": "john_worker",
            "email": "john@example.com",
            "role": "worker",
            "updated_at": null
        }
    }
    
    JSON Error Response (400):
    {
        "success": false,
        "error": "Username is already registered."
    }
    
    Validates:
    - Username is provided and unique
    - Email is provided and unique
    - Password is provided and meets requirements
    - Password confirmation matches (if provided)
    - Role is valid (Worker, Planner, Client)
    
    Security:
    - Creation of 'admin' role is blocked here for security.
    """
    if request.method == "POST":
        # Extract data based on content type
        if request.is_json:
            # JSON request from API/PWA
            data = request.get_json()
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
            password_confirm = data.get("password_confirm")
            role = data.get("role")
        else:
            # Form data from HTML
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")
            password_confirm = request.form.get("password_confirm")
            role = request.form.get("role")
        
        error = None

        # Validation
        if not username:
            error = "Username is required."
        elif not email:
            error = "Email is required."
        elif not password:
            error = "Password is required."
        
        # --- SECURITY FIX: Block 'admin' role creation ---
        # The form only offers worker, planner, client, but we must enforce server-side
        valid_roles = ["worker", "planner", "client"]
        if not role or role not in valid_roles:
            error = "Valid role is required (Worker, Planner, or Client)."
        # -------------------------------------------------

        # Password confirmation validation (if provided)
        elif password_confirm and password != password_confirm:
            error = "Passwords do not match. Please ensure both password fields are identical."

        # Check for duplicate username
        elif User.query.filter_by(username=username).first() is not None:
            error = f"User {username} is already registered."
        
        # Check for duplicate email
        elif User.query.filter_by(email=email).first() is not None:
            error = f"Email {email} is already registered."

        # If validation passes, create the user
        if error is None:
            admin = g.user  # Current admin performing the action
            user = admin.create_user(
                username=username,
                email=email,
                role=role,
                password=password,
            )
            try:
                db.session.add(user)
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None
                }
                
                db.session.commit()
                
                success_message = f"User '{username}' created successfully with role '{role}'."
                
                # Return appropriate response based on request type
                if request.is_json:
                    # JSON response for API clients
                    return jsonify({
                        "success": True,
                        "message": success_message,
                        "user": user_data, 
                        
                    }), 201  # 201 Created
                else:
                    # HTML redirect for browser clients
                    flash(success_message, "success")
                    return redirect(url_for("admin.list_users"))
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred: {str(e)}"

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

    # GET request: show user creation form
    return render_template("admin/create_user.html")


@bp.route("/users/<user_id>/edit", methods=["GET", "POST", "PATCH"])
@login_required
@admin_required
def edit_user(user_id):
    """
    Edit an existing user.
    
    GET: Display user edit form (HTML) or return user data (JSON)
    POST/PATCH: Process form and update user
    
    Supports PARTIAL UPDATES - only include fields you want to change!
    
    Accepts two content types:
    1. application/x-www-form-urlencoded (HTML forms)
    2. application/json (API/PWA requests)
    
    JSON Request Examples:
    
    Full Update:
    {
        "username": "john_worker",
        "email": "john.new@example.com",
        "role": "planner",
        "password": "newsecure123",
        "password_confirm": "newsecure123"
    }
    
    Partial Update (only email):
    {
        "email": "john.newest@example.com"
    }
    
    Partial Update (only password):
    {
        "password": "newpassword123",
        "password_confirm": "newpassword123"
    }
    
    Partial Update (only role):
    {
        "role": "planner"
    }
    
    JSON Success Response (200):
    {
        "success": true,
        "message": "User 'john_worker' updated successfully.",
        "user": {
            "id": "uuid-here",
            "username": "john_worker",
            "email": "john.newest@example.com",
            "role": "planner",
            "updated_at": "2025-01-21T09:30:00Z"
        }
    }
    
    JSON Error Response (400):
    {
        "success": false,
        "error": "Email is already registered."
    }
    
    Validates:
    - Username is unique (if provided and changed)
    - Email is unique (if provided and changed)
    - New password matches confirmation (if provided)
    - Password meets minimum length requirements (if provided)
    
    Security:
    - Admins cannot change their own role (enforced in backend)
    - Password confirmation is required for password changes
    """
    user = User.query.get_or_404(user_id)
    
    if request.method in ["POST", "PATCH"]:
        # Extract data based on content type
        if request.is_json:
            # JSON request from API/PWA
            data = request.get_json()
            # Default to current values if not provided (PARTIAL UPDATE SUPPORT)
            username = data.get("username", user.username)
            email = data.get("email", user.email)
            new_password = data.get("password")
            password_confirm = data.get("password_confirm")
            role = data.get("role", user.role)
        else:
            # Form data from HTML
            # For HTML forms, we expect all fields to be present
            username = request.form.get("username", user.username)
            email = request.form.get("email", user.email)
            new_password = request.form.get("password")
            password_confirm = request.form.get("password_confirm")
            role = request.form.get("role", user.role)
        
        # Role handling: prevent self role changes
        # Security check - never trust client data for this!
        if str(user.id) == str(g.user.id):
            role = user.role  # Keep current role for own account
        
        error = None
        
        # Track what changed (for better response messages)
        changes = []
        
        # Validation: Username (only if changed)
        if username != user.username:
            if not username:
                error = "Username cannot be empty."
            else:
                found_by_username = User.query.filter_by(username=username).first()
                if found_by_username and found_by_username.id != user.id:
                    error = f"Username {username} is already registered."
                else:
                    changes.append("username")
        
        # Validation: Email (only if changed)
        if not error and email != user.email:
            if not email:
                error = "Email cannot be empty."
            else:
                found_by_email = User.query.filter_by(email=email).first()
                if found_by_email and found_by_email.id != user.id:
                    error = f"Email {email} is already registered."
                else:
                    changes.append("email")
        
        # Validation: Role (only if changed and allowed)
        if not error and role != user.role:
            valid_roles = ["admin", "worker", "planner", "client"]
            if not role or role not in valid_roles:
                error = "Valid role is required."
            elif str(user.id) == str(g.user.id):
                error = "You cannot change your own role."
            else:
                changes.append("role")
        
        # Validation: Password (only if provided)
        if not error and new_password:
            if not password_confirm:
                error = "Password confirmation is required when changing password."
            elif new_password != password_confirm:
                error = "Passwords do not match. Please ensure both password fields are identical."
            elif not user.check_password(new_password):
                changes.append("password")
        
        # If all validation passes, update the user
        if error is None:
            # Check if there are any actual changes
            if not changes:
                message = "No changes detected."
                
                if request.is_json:
                    return jsonify({
                        "success": True,
                        "message": message,
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "role": user.role,
                            "updated_at": user.updated_at.isoformat() if user.updated_at else None
                        }
                    }), 200
                else:
                    flash(message, "info")
                    return redirect(url_for("admin.list_users"))
            
            # Apply changes
            admin = g.user  # Current admin performing the action
            
            # Update user information (only changed fields)
            if "username" in changes or "email" in changes or "role" in changes:
                admin.update_user_info(
                    user, 
                    new_email=email if "email" in changes else None,
                    new_username=username if "username" in changes else None,
                    new_role=role if "role" in changes else None
                )
            
            # Update password if provided
            if "password" in changes:
                admin.set_user_password(user, new_password)
            
            try:
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None
                }
                
                db.session.commit()
                
                # Create detailed success message
                if len(changes) == 1:
                    change_text = changes[0]
                elif len(changes) == 2:
                    change_text = f"{changes[0]} and {changes[1]}"
                else:
                    change_text = ", ".join(changes[:-1]) + f", and {changes[-1]}"
                
                success_message = f"User '{username}' updated successfully. Changed: {change_text}."
                
                # Return appropriate response based on request type
                if request.is_json:
                    # JSON response for API clients
                    return jsonify({
                        "success": True,
                        "message": success_message,
                        "changes": changes,
                        "user": user_data
                    }), 200
                else:
                    # HTML redirect for browser clients
                    flash(success_message, "success")
                    return redirect(url_for("admin.list_users"))
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred: {str(e)}"

        # Handle validation/update errors
        if request.is_json:
            # Return JSON error for API clients
            return jsonify({
                "success": False,
                "error": error
            }), 400
        else:
            # Flash message for HTML clients
            flash(error, "error")

    # GET request
    if request.is_json:
        # Return current user data for JSON clients
        return jsonify({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "login_at": user.login_at.isoformat() if user.login_at else None
            }
        }), 200
    else:
        # HTML form
        return render_template("admin/edit_user.html", user=user)


@bp.route("/users/<user_id>/delete", methods=["POST", "DELETE"])
@login_required
@admin_required
def delete_user(user_id):
    """
    Delete a user.
    
    POST or DELETE: Delete the user
    
    Accepts both POST (for HTML forms) and DELETE (for RESTful API).
    
    JSON Success Response (200):
    {
        "success": true,
        "message": "User 'john_worker' deleted successfully."
    }
    
    JSON Error Response (400):
    {
        "success": false,
        "error": "You cannot delete your own account."
    }
    
    Security:
    - Admins cannot delete themselves
    """
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if str(user.id) == str(g.user.id):
        error_message = "You cannot delete your own account."
        
        if request.is_json:
            return jsonify({
                "success": False,
                "error": error_message
            }), 400
        else:
            flash(error_message, "error")
            return redirect(url_for("admin.list_users"))
    
    # Store username before deleting
    deleted_username = user.username
    
    try:
        db.session.delete(user)
        db.session.commit()
        
        success_message = f"User '{deleted_username}' deleted successfully."
        
        if request.is_json:
            return jsonify({
                "success": True,
                "message": success_message
            }), 200
        else:
            flash(success_message, "success")
            return redirect(url_for("admin.list_users"))
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
            return redirect(url_for("admin.list_users"))