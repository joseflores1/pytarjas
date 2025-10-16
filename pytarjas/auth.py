# pytarjas/auth.py
"""
Authentication blueprint for user registration, login, and logout.

This module handles all user authentication using SQLAlchemy and PostgreSQL.
"""

import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from pytarjas.models.user_models import db, User

# Create blueprint with URL prefix /auth
bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Register a new user.
    
    GET: Display registration form
    POST: Process registration form and create new user
    
    Validates:
    - Username is provided and unique
    - Email is provided and unique  
    - Password is provided
    """
    if request.method == "POST":
        username = request.form["username"]
        email = request.form.get("email")  # Get email from form
        password = request.form["password"]
        error = None

        # Validation
        if not username:
            error = "Username is required."
        elif not email:
            error = "Email is required."
        elif not password:
            error = "Password is required."
        elif User.query.filter_by(username=username).first() is not None:
            error = f"User {username} is already registered."
        elif User.query.filter_by(email=email).first() is not None:
            error = f"Email {email} is already registered."

        if error is None:
            # Create new user (default role is 'user')
            # You can change role to 'admin', 'worker', 'planner', 'client'
            user = User(
                username=username,
                email=email,
                role="user"  # Default role, change as needed
            )
            user.set_password(password)  # Hash the password
            
            try:
                db.session.add(user)
                db.session.commit()
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for("auth.login"))
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred: {str(e)}"

        flash(error, "error")

    return render_template("auth/register.html")


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
        user = User.query.filter_by(username=username).first()

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
        g.user = User.query.get(user_id)


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


def role_required(*roles):
    """
    Decorator to require specific role(s) for a view.
    
    Usage:
        @bp.route('/admin-only')
        @login_required
        @role_required('admin')
        def admin_view():
            return "Only admins see this"
        
        @bp.route('/workers-and-planners')
        @login_required
        @role_required('worker', 'planner')
        def worker_planner_view():
            return "Workers and planners see this"
    
    If the user doesn't have the required role, shows 403 error.
    """
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if g.user is None:
                return redirect(url_for("auth.login"))
            if g.user.role not in roles:
                flash("You don't have permission to access this page.", "error")
                return redirect(url_for("index"))
            return view(**kwargs)
        return wrapped_view
    return decorator
#import functools

#from flask import (
    #Blueprint, flash, g, redirect, render_template, request, session, url_for
#)
#from werkzeug.security import check_password_hash, generate_password_hash

#from pytarjas.dbs import get_db

#bp = Blueprint("auth", __name__, url_prefix="/auth")

#@bp.route("/register", methods=["GET", "POST"])
#def register():
    #if request.method == "POST":
        #username = request.form["username"]
        #password = request.form["password"]
        #db = get_db()
        #error = None

        #if not username:
            #error = "Username is required."
        #elif not password:
            #error = "Password is required."

        #if error is None:
            #try:
                #db.execute(
                    #"INSERT INTO user (username, password) VALUES (?, ?)",
                    #(username, generate_password_hash(password)),
                #)
                #db.commit()
            #except db.IntegrityError:
                #error = f"User {username} is already registered."
            #else:
                #return redirect(url_for("auth.login"))

        #flash(error, "error")

    #return render_template("auth/register.html")

#@bp.route("/login", methods=["GET", "POST"])
#def login():
    #if request.method == "POST":
        #username = request.form["username"]
        #password = request.form["password"]
        #db = get_db()
        #error = None
        #user = db.execute(
                #"SELECT * FROM user WHERE username = ?",
                #(username,)
        #).fetchone()

        #if user is None:
            #error = "Incorrect username."
        #elif not check_password_hash(user["password"], password):
            #print(user)
            #error = "Incorrect password"

        #if error is None:
                #session.clear()
                #session["user_id"] = user["id"]
                #return redirect(url_for("index"))

        #flash(error)

    #return render_template("auth/login.html")

#@bp.before_app_request
#def load_logged_in_user():
    #user_id = session.get("user_id")

    #if user_id is None:
        #g.user = None
    #else:
        #g.user = get_db().execute(
            #"SELECT * FROM user WHERE id = ?",
            #(user_id,)
        #).fetchone()

#@bp.route("/logout")
#def logout():
    #session.clear()
    #return redirect(url_for("index"))

#def login_required(view):
    #@functools.wraps(view)
    #def wrapped_view(**kwargs):
        #if g.user is None:
            #return redirect(url_for("auth.login"))

        #return view(**kwargs)

    #return wrapped_view