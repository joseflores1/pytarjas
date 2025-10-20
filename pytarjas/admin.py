# pytarjas/admin.py
"""
Admin blueprint for user management.

Only users with 'admin' role can access these views.
Admins can create, list, edit, and delete users.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for, session, g
from pytarjas.models.user_models import db, User, Admin, Worker, Planner, Client #noqa
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
    """
    user_count = session.query(User).count()
    admin_count = session.query(User).filter_by(role="admin").count()
    worker_count = session.query(User).filter_by(role="worker").count()
    planner_count = session.query(User).filter_by(role="planner").count()
    client_count = session.query(User).filter_by(role="client").count()
    
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
    Allows filtering by role.
    """
    # Get role filter from query parameter
    role_filter = request.args.get("role")
    
    if role_filter:
        users = session.query(User).filter_by(role=role_filter).order_by(User.created_at.desc()).all()
    else:
        users = session.query(User).order_by(User.created_at.desc()).all()
    
    return render_template("admin/list_users.html", users=users, role_filter=role_filter)


@bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    """
    Create a new user.
    
    GET: Display user creation form
    POST: Process form and create user
    
    Validates:
    - Username is provided and unique
    - Email is provided and unique
    - Password is provided
    - Role is valid
    """
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]
        error = None

        # Validation
        if not username:
            error = "Username is required."
        elif not email:
            error = "Email is required."
        elif not password:
            error = "Password is required."
        elif not role or role not in ["admin", "worker", "planner", "client"]:
            error = "Valid role is required."
        elif session.query(User).filter_by(username=username).first() is not None:
            error = f"User {username} is already registered."
        elif session.query(User).filter_by(email=email).first() is not None:
            error = f"Email {email} is already registered."

        if error is None:
            admin=g.user
            user=admin.create_user(
                username=username,
                email=email,
                role=role,
                password=password,
            )
            try:
                db.session.add(user)
                db.session.commit()
                flash(f"User '{username}' created successfully with role '{role}'.", "success")
                return redirect(url_for("admin.list_users"))
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred: {str(e)}"

        flash(error, "error")

    return render_template("admin/create_user.html")


@bp.route("/users/<user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    """
    Edit an existing user.
    
    GET: Display user edit form
    POST: Process form and update user
    
    Admins cannot delete themselves or change their own role.
    """
    user = session.query(User).get_or_404(user_id)
    
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        role = request.form["role"]
        new_password = request.form.get("password")  # Optional
        error = None

        found_by_username = session.query(User).filter_by(username=username).first()
        found_by_email= session.query(User).filter_by(email=email).first()
        # Validation
        if not username:
            error = "Username is required."
        elif not email:
            error = "Email is required."
        elif not role or role not in ["admin", "worker", "planner", "client"]:
            error = "Valid role is required."
        # Check if username is taken by another user
        elif (found_by_username is not None) and (found_by_username.id != user_id):
            error = f"Username {username} is already registered."
        elif (found_by_username is not None) and (found_by_username.id == user_id): 
            error="New username is the same as old username."
        # Check if email is taken by another user
        elif (found_by_email is not None) and (found_by_email.id != user_id):
            error = f"Email {email} is alredy registered."
        elif (found_by_email is not None) and (found_by_email.id == user_id):  
            error="New email is the same as old email."

        if error is None:
            admin=g.user 
            admin.update_user_info(user, new_email=email, new_username=username, new_role=role)
            # Update password if provided
            if new_password:
                admin.set_user_password(user, new_password)
            
            try:
                db.session.commit()
                flash(f"User '{username}' updated successfully.", "success")
                return redirect(url_for("admin.list_users"))
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred: {str(e)}"

        flash(error, "error")

    return render_template("admin/edit_user.html", user=user)


@bp.route("/users/<user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    """
    Delete a user.
    
    POST: Delete the user
    
    Admins cannot delete themselves.
    """
    from flask import g
    
    user = session.query(User).get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == g.user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.list_users"))
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f"User '{user.username}' deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "error")
    
    return redirect(url_for("admin.list_users"))