# pytarjas/auth.py
"""
Authentication blueprint for user login and logout.

Users can only login - registration is disabled.
Only admins can create users via the admin panel.
"""

import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from pytarjas.models.user_models import db, User #noqa

# Create blueprint with URL prefix /auth
bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Log in an existing user.
    
    GET: Display login form
    POST: Process login form and create session
    
    Validates:
    - Username exists
    - Password is correct
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        error = None
        
        # Query user by username
        user = session.query(User).filter_by(username=username).first()

        if user is None:
            error = "Incorrect username."
        elif not user.check_password(password):
            error = "Incorrect password."

        if error is None:
            # Clear any existing session
            session.clear()
            # Store user ID in session
            session["user_id"] = user.id
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("index"))

        flash(error, "error")

    return render_template("auth/login.html")


@bp.before_app_request
def load_logged_in_user():
    """
    Load the logged-in user before each request.
    
    This function runs before every request. It checks if a user_id
    is stored in the session, and if so, loads that user from the
    database and stores it in g.user (available throughout the request).
    """
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        # Load user from database using SQLAlchemy
        g.user = session.query(User).get(user_id)


@bp.route("/logout")
def logout():
    """
    Log out the current user.
    
    Clears the session and redirects to the index page.
    """
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


def login_required(view):
    """
    Decorator to require login for a view.
    
    Usage:
        @bp.route('/protected')
        @login_required
        def protected_view():
            return "Only logged-in users see this"
    
    If the user is not logged in, redirects to the login page.
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    
    return wrapped_view


def admin_required(view):
    """
    Decorator to require admin role for a view.
    
    Usage:
        @bp.route('/admin-panel')
        @login_required
        @admin_required
        def admin_panel():
            return "Only admins see this"
    
    If the user is not an admin, redirects with error message.
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        if g.user.role != "admin":
            flash("You don't have permission to access this page.", "error")
            return redirect(url_for("index"))
        return view(**kwargs)
    
    return wrapped_view