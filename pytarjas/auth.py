# pytarjas/auth.py
"""
Authentication blueprint for user login and logout.

Supports both traditional HTML forms and JSON API requests.
This dual approach allows:
- HTML forms for browser-based admin interface
- JSON API for Progressive Web App (PWA) and mobile clients
"""

import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)
from datetime import timezone, datetime
from pytarjas.models.user_models import db, User

# Create blueprint with URL prefix /auth
bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Log in an existing user.
    
    GET: Display login form (HTML)
    POST: Process login and create session
    
    Accepts two content types:
    1. application/x-www-form-urlencoded (HTML forms)
    2. application/json (API/PWA requests)
    
    JSON Request Example:
    {
        "username": "admin",
        "password": "secret123"
    }
    
    JSON Success Response (200):
    {
        "success": true,
        "message": "Welcome back, admin!",
        "user": {
            "id": "uuid-here",
            "username": "admin",
            "role": "admin",
            "email": "admin@example.com"
        }
    }
    
    JSON Error Response (401):
    {
        "success": false,
        "error": "Incorrect password."
    }
    """
    if request.method == "POST":
        # Detect request type and extract credentials
        if request.is_json:
            # JSON request from API/PWA
            data = request.get_json()
            username = data.get("username")
            password = data.get("password")
        else:
            # Form data from HTML
            username = request.form.get("username")
            password = request.form.get("password")
        
        error = None
        
        # Validation
        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        else:
            # Query user by username
            user = User.query.filter_by(username=username).first()

            if user is None:
                error = "Incorrect username."
            elif not user.check_password(password):
                error = "Incorrect password."
        
        # If authentication successful
        if error is None:
            try:
                # Update login timestamp
                setattr(User, "login_at", datetime.now(timezone.utc))
                user.login_at = User.login_at 
                db.session.commit()
                
                # Clear any existing session and create new one
                session.clear()
                session["user_id"] = user.id
                
                # Return appropriate response based on request type
                if request.is_json:
                    # JSON response for API clients (PWA)
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
                    # HTML redirect for browser clients
                    flash(f"Welcome back, {user.username}!", "success")
                    if user.role=="admin":
                        return redirect(url_for("admin.index"))
                    if user.role=="worker":
                        return redirect(url_for("worker.index"))
                    if user.role=="planner":
                        return redirect(url_for("planner.index"))
                    if user.role=="client":
                        return redirect(url_for("client.index"))
 
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred: {str(e)}"
        
        # Handle authentication errors
        if request.is_json:
            # Return JSON error for API clients
            return jsonify({
                "success": False,
                "error": error
            }), 401
        else:
            # Flash message for HTML clients
            flash(error, "error")

    # GET request: show login form
    return render_template("auth/login.html")


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    """
    Log out the current user.
    
    Supports both GET (HTML) and POST (API) requests.
    Clears the session and returns appropriate response.
    
    JSON Response (200):
    {
        "success": true,
        "message": "You have been logged out."
    }
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
    
    This endpoint is useful for PWA to check authentication status
    without triggering a redirect.
    
    JSON Response when logged in (200):
    {
        "authenticated": true,
        "user": {
            "id": "uuid",
            "username": "admin",
            "role": "admin",
            "email": "admin@example.com"
        }
    }
    
    JSON Response when not logged in (401):
    {
        "authenticated": false
    }
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
    
    This function runs before every request. It checks if a user_id
    is stored in the session, and if so, loads that user from the
    database and stores it in g.user (available throughout the request).
    
    This works seamlessly for both HTML and JSON requests because
    Flask sessions work with cookies, which are automatically sent
    by browsers and can be configured in fetch() requests.
    """
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        # Load user from database using SQLAlchemy
        g.user = User.query.get(user_id)


def login_required(view):
    """
    Decorator to require login for a view.
    
    Usage:
        @bp.route('/protected')
        @login_required
        def protected_view():
            return "Only logged-in users see this"
    
    Behavior:
    - HTML requests: Redirects to login page
    - JSON requests: Returns 401 with error message
    
    This allows the same endpoint to work for both browser
    and API/PWA clients.
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            if request.is_json:
                # Return JSON error for API clients
                return jsonify({
                    "success": False,
                    "error": "Authentication required."
                }), 401
            else:
                flash("Please log in to access this page.", "warning")
                # Redirect HTML clients to login
                return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    """
    Decorator to require admin role for a view.
    
    Must be used AFTER @login_required decorator.
    
    Usage:
        @bp.route('/admin-only')
        @login_required
        @admin_required
        def admin_view():
            return "Only admins see this"
    
    Behavior:
    - Checks if user has 'admin' role
    - HTML requests: Shows 403 error page
    - JSON requests: Returns 403 with error message
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user.role != "admin":
            if request.is_json:
                # Return JSON error for API clients
                return jsonify({
                    "success": False,
                    "error": "Admin privileges required."
                }), 403
            else:
                # HTML clients get 403 forbidden
                from flask import abort
                abort(403)

        return view(**kwargs)

    return wrapped_view