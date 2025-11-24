# pytarjas/auth.py
"""
...
"""
from functools import wraps
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify, abort
)
from datetime import timezone, datetime
from pytarjas.models.user_models import db, User

# Create blueprint with URL prefix /auth
bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Log in an existing user.
    """
    # FIX: Redirige inmediatamente si el usuario ya está autenticado (Control UX/Seguridad)
    if g.user is not None:
        if g.user.role == "admin":
            return redirect(url_for("admin.index"))
        if g.user.role == "planner":
            # Redirect to planner.list_planifications (the root of the planner blueprint)
            return redirect(url_for("planner.list_planifications"))
        if g.user.role == "worker":
            return redirect(url_for("worker.index"))
        if g.user.role == "client":
            return redirect(url_for("client.index"))
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            email = data.get("email") 
            password = data.get("password")
        else:
            email = request.form.get("email") 
            password = request.form.get("password")
        
        error = None
        
        if not email:
            error = "Email is required."
        elif not password:
            error = "Password is required."
        else:
            user = User.query.filter_by(email=email).first()

            if user is None:
                error = "Incorrect email."
            elif not user.check_password(password):
                error = "Incorrect password."
        
        if error is None:
            try:
                setattr(User, "login_at", datetime.now(timezone.utc))
                user.login_at = User.login_at 
                db.session.commit()
                
                session.clear()
                session["user_id"] = user.id
                
                if request.is_json:
                    return jsonify({
                        "success": True,
                        "message": f"Welcome back, {user.username}!", 
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "role": user.role,
                            "email": user.email
                        }
                    }), 200
                else:
                    flash(f"Welcome back, {user.username}!", "success")
                    # Update redirects to use the root of each blueprint
                    if user.role=="admin":
                        return redirect(url_for("admin.index"))
                    if user.role=="worker":
                        return redirect(url_for("worker.index"))
                    if user.role=="planner":
                        return redirect(url_for("planner.list_planifications"))
                    if user.role=="client":
                        return redirect(url_for("client.index"))
 
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred: {str(e)}"
        
        if request.is_json:
            return jsonify({
                "success": False,
                "error": error
            }), 401
        else:
            flash(error, "error")

    return render_template("auth/login.html")


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    """
    Log out the current user.
    """
    session.clear()
    
    if request.is_json:
        return jsonify({
            "success": True,
            "message": "You have been logged out."
        }), 200
    else:
        flash("You have been logged out.", "info")
        return redirect(url_for("auth.login"))


@bp.route("/session", methods=["GET"])
def check_session():
    """
    Check if user is logged in and return session info.
    """
    if g.user:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": g.user.id,
                "username": g.user.username,
                "role": g.user.role,
                "email": g.user.email
            }
        }), 200
    else:
        return jsonify({
            "authenticated": False
        }), 401


@bp.before_app_request
def load_logged_in_user():
    """
    Load the logged-in user before each request.
    """
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)


def login_required(view):
    """
    Decorator to require login for a view.
    """
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            if request.is_json:
                return jsonify({
                    "success": False,
                    "error": "Authentication required."
                }), 401
            else:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    """
    Decorator to require admin role for a view.
    """
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user.role != "admin":
            if request.is_json:
                return jsonify({
                    "success": False,
                    "error": "Admin privileges required."
                }), 403
            else:
                from flask import abort
                abort(403)

        return view(**kwargs)

    return wrapped_view

def task_access_required(view):
    """
    Decorator to require task access permissions.
    """
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user.role == "client":
            if request.is_json or request.headers.get("Accept") == "application/json":
                return jsonify({
                    "success": False,
                    "error": "Access denied. Clients cannot access task endpoints."
                }), 403
            else:
                abort(403)
        
        return view(**kwargs)
    
    return wrapped_view


def form_access_required(view):
    """
    Decorator to require form management permissions.
    """
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user.role not in ["admin", "planner"]:
            if request.is_json or request.headers.get("Accept") == "application/json":
                return jsonify({
                    "success": False,
                    "error": "Access denied. Only admins and planners can manage forms."
                }), 403
            else:
                abort(403)
        
        return view(**kwargs)
    
    return wrapped_view


def assignment_access_required(view):
    """
    Decorator to require task assignment permissions.
    """
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user.role not in ["admin", "planner"]:
            if request.is_json or request.headers.get("Accept") == "application/json":
                return jsonify({
                    "success": False,
                    "error": "Access denied. Only admins and planners can assign tasks."
                }), 403
            else:
                abort(403)
        
        return view(**kwargs)
    
    return wrapped_view