# pytarjas/__init__.py
import os
from flask import Flask, redirect, url_for, session, g


def create_app(test_config=None):
    """
    Create and configure the Flask application.
    
    This is the application factory pattern recommended by Flask.
    """
    # Create Flask app instance
    app = Flask(__name__, instance_relative_config=True)
    
    # ... [Configuration loading and instance path setup remain unchanged] ...
    if test_config is None:
        # Load configuration from config.py based on APP_ENV
        app_env = os.getenv('FLASK_ENV', 'development')
        config_class = f'config.{app_env.capitalize()}Config'
        app.config.from_object(config_class)
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
    
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    try:
        upload_path = os.path.join(app.instance_path, app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_path)
    except OSError:
        pass
    
    # Initialize Flask-SQLAlchemy extension
    from .models.user_models import db
    db.init_app(app)
    
    # Import all models so SQLAlchemy knows about them
    from .models import user_models, docs_models  # noqa
    
    with app.app_context():
        db.create_all()
    
    # Register blueprints
    from . import auth
    app.register_blueprint(auth.bp)
    
    from . import admin
    app.register_blueprint(admin.bp)
    
    from . import tasks
    app.register_blueprint(tasks.bp)

    from . import worker
    app.register_blueprint(worker.bp)

    from . import forms
    app.register_blueprint(forms.bp)
    
    from . import planner # Asegurar que la redirección a 'planner' funcione
    app.register_blueprint(planner.bp)

    # ============================================================================
    # FIX DE SEGURIDAD: DESHABILITAR CACHÉ DEL NAVEGADOR (BFCACHE)
    # Esto previene que el botón 'Atrás' muestre la página del usuario anterior.
    # ============================================================================
    @app.after_request
    def set_secure_headers(response):
        """Añade cabeceras para prevenir caching de la página por el navegador."""
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # ============================================================================
    # ROOT ROUTE: Redirect to appropriate page based on authentication
    # ============================================================================
    @app.route("/")
    def index():
        """
        Root route handler.
        """
        
        # Check if user is logged in by looking for user_id in session
        if "user_id" not in session:
            # Not logged in → send to login page
            return redirect(url_for("auth.login"))
        
        # User is logged in → get their info to determine dashboard
        from pytarjas.models.user_models import User
        user = User.query.get(session["user_id"])
        
        if user is None:
            # Session has invalid user_id (maybe user was deleted)
            # Clear session and send to login
            session.clear()
            return redirect(url_for("auth.login"))
        
        # Route based on user role
        if user.role == "admin":
            return redirect(url_for("admin.index"))
        elif user.role == "planner":
            return redirect(url_for("planifications.list_planifications"))
        elif user.role == "worker":
            return redirect(url_for("worker.index"))
        elif user.role == "client":
            # Redirigir a worker.index ya que /client/ no existe aún
            return redirect(url_for("worker.index"))
        else:
            # Unknown role → send to login
            session.clear()
            return redirect(url_for("auth.login"))
    
    return app