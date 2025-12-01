# pytarjas/blueprints/artifacts/users.py
"""
Users API blueprint for agnostic user management.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for, g, jsonify
from pytarjas.models.user_models import db, User, Admin
from pytarjas.auth import login_required, user_management_required # Import the agnostic decorator

# Create blueprint with URL prefix /users
bp = Blueprint("users", __name__, url_prefix="/users")

# ============================================================================
# ROUTE: List all users (GET /users/)
# ============================================================================
@bp.route("/", methods=["GET"])
@login_required
@user_management_required
def list_users():
    """
    List all users in the system.
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
    
    # FIX: Template path changed from "admin/list_users.html" to "users/list_users.html"
    return render_template("users/list_users.html", users=users, role_filter=role_filter)


# ============================================================================
# ROUTE: Create a new user (POST /users/create)
# ============================================================================
@bp.route("/create", methods=["GET", "POST"])
@login_required
@user_management_required
def create_user():
    """
    Create a new user.
    """
    if request.method == "POST":
        # Extract data based on content type
        if request.is_json:
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

        # Validation (Logic directly copied from old admin.py)
        if not username:
            error = "Username is required."
        elif not email:
            error = "Email is required."
        elif not password:
            error = "Password is required."
        
        valid_roles = ["worker", "planner", "client"]
        if not role or role not in valid_roles:
            error = "Valid role is required (Worker, Planner, or Client)."

        elif password_confirm and password != password_confirm:
            error = "Passwords do not match. Please ensure both password fields are identical."

        elif User.query.filter_by(username=username).first() is not None:
            error = f"User {username} is already registered."
        
        elif User.query.filter_by(email=email).first() is not None:
            error = f"Email {email} is already registered."

        if error is None:
            # Create a temporary Admin instance to use the factory method
            creator = Admin()
            user = creator.create_user(
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
                
                if request.is_json:
                    return jsonify({
                        "success": True,
                        "message": success_message,
                        "user": user_data,
                        
                    }), 201
                else:
                    flash(success_message, "success")
                    # FIX: Redirect to the users blueprint list view
                    return redirect(url_for("users.list_users"))
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred: {str(e)}"

        if request.is_json:
            return jsonify({
                "success": False,
                "error": error
            }), 400
        else:
            flash(error, "error")

    # FIX: Corrected template path from "users/create_user.html" to "users/create_users.html"
    return render_template("users/create_users.html")


# ============================================================================
# ROUTE: Get/Edit an existing user (GET/POST/PATCH /users/<id>/edit)
# ============================================================================
@bp.route("/<user_id>/edit", methods=["GET", "POST", "PATCH"])
@login_required
@user_management_required
def edit_user(user_id):
    """
    Edit an existing user.
    """
    user = User.query.get_or_404(user_id)
    
    # Initialize error for the scope of the POST/PATCH logic
    error = None 

    if request.method in ["POST", "PATCH"]:
        if request.is_json:
            data = request.get_json()
            username = data.get("username", user.username)
            email = data.get("email", user.email)
            new_password = data.get("password")
            password_confirm = data.get("password_confirm")
            role = data.get("role", user.role)
        else:
            username = request.form.get("username", user.username)
            email = request.form.get("email", user.email)
            new_password = request.form.get("password")
            password_confirm = request.form.get("password_confirm")
            # If form data is present, retrieve role.
            role = request.form.get("role", user.role)
        
        # Security check - prevent self role changes
        if str(user.id) == str(g.user.id):
            # If editing self, grab the role from the database to prevent accidental self-demotion
            role = user.role
        
        changes = []
        
        # NEW SECURITY BLOCK: Block editing another Admin
        if user.role == "admin" and str(user.id) != str(g.user.id):
            error = "You cannot edit another Administrator's account."
        
        # Validation: Username (only if changed)
        if not error and username != user.username:
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
                # SECURITY FIX: Explicit error if user attempts to change their own role
                error = "You cannot change your own role."
            # NEW SECURITY FIX: Block assigning the 'admin' role (even by other admins)
            elif role == "admin":
                 error = "Assigning the 'Admin' role is blocked for security and self-governance purposes."
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
        
        if error is None:
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
                    # UX FIX: Flash message and stay on the edit page
                    flash(message, "info")
                    return render_template("users/edit_users.html", user=user)
            
            # Apply changes using a temporary Admin instance (as it holds update_user_info/set_user_password)
            updater = Admin()
            
            if "username" in changes or "email" in changes or "role" in changes:
                updater.update_user_info(
                    user,
                    new_email=email if "email" in changes else None,
                    new_username=username if "username" in changes else None,
                    new_role=role if "role" in changes else None
                )
            
            if "password" in changes:
                updater.set_user_password(user, new_password)
            
            try:
                # CRITICAL FIX STEP 1: Store ID before commit invalidates the object
                current_user_id = user.id
                
                is_self_edit = str(user.id) == str(g.user.id)

                db.session.commit()
                
                # CRITICAL FIX STEP 2: Expunge the stale object and re-fetch it to resolve DetachedInstanceError
                # We need to detach the old Python object which now refers to an invalidated database row/class.
                db.session.expunge(user) 
                
                # CRITICAL FIX STEP 3: Re-fetch the fresh object using the stored ID
                user = User.query.get(current_user_id) 
                
                # NEW FIX: If current user was edited, ensure g.user points to the fresh object
                if is_self_edit:
                    g.user = user 
                
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None
                }
                
                if len(changes) == 1:
                    change_text = changes[0]
                elif len(changes) == 2:
                    change_text = f"{changes[0]} and {changes[1]}"
                else:
                    change_text = ", ".join(changes[:-1]) + f", and {changes[-1]}"
                
                success_message = f"User '{username}' updated successfully. Changed: {change_text}."
                
                if request.is_json:
                    return jsonify({
                        "success": True,
                        "message": success_message,
                        "changes": changes,
                        "user": user_data
                    }), 200
                else:
                    # UX FIX: Flash message and stay on the edit page
                    flash(success_message, "success")
                    return render_template("users/edit_users.html", user=user)
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred: {str(e)}"
                
                # CRITICAL FIX: Explicit return on database error
                if request.is_json:
                    return jsonify({"success": False, "error": error}), 500
                else:
                    
                    flash(error, "error")
                    return render_template("users/edit_users.html", user=user)


        # If execution reaches here, it means 'error' was set by validation logic.
        if request.is_json:
            return jsonify({
                "success": False,
                "error": error
            }), 400
        else:
            # FIX: Explicit return for validation error path
            flash(error, "error")
            return render_template("users/edit_users.html", user=user)

    # This handles the initial GET request (and acts as the final return for the function)
    if request.is_json:
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
        return render_template("users/edit_users.html", user=user)


# ============================================================================
# ROUTE: Delete a user (POST/DELETE /users/<id>/delete)
# ============================================================================
@bp.route("/<user_id>/delete", methods=["POST", "DELETE"])
@login_required
@user_management_required
def delete_user(user_id):
    """
    Delete a user.
    """
    user = User.query.get_or_404(user_id)
    
    # NEW SECURITY FIX: Block deletion of any Admin
    if user.role == "admin":
        error_message = "Deletion blocked: You cannot delete an Administrator account."
        
        if request.is_json:
            return jsonify({
                "success": False,
                "error": error_message
            }), 403
        else:
            flash(error_message, "error")
            return redirect(url_for("users.list_users"))
    
    # Prevent deletion of own account (this check still works for non-admins trying to delete themselves)
    if str(user.id) == str(g.user.id):
        error_message = "You cannot delete your own account."
        
        if request.is_json:
            return jsonify({
                "success": False,
                "error": error_message
            }), 400
        else:
            flash(error_message, "error")
            return redirect(url_for("users.list_users"))
    
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
            return redirect(url_for("users.list_users"))
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
            return redirect(url_for("users.list_users"))