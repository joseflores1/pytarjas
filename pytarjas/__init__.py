# pytarjas/__init__.py
import os
from flask import Flask, redirect, url_for, session, send_from_directory # NEW: Import send_from_directory
from .models.user_models import User

def create_app(test_config=None):
    """
    Create and configure the Flask application.
    """
    # Create Flask app instance
    app = Flask(__name__, instance_relative_config=True)
    
    if test_config is None:
        # FIX: Load configuration dynamically based on FLASK_ENV
        app_env = os.getenv('FLASK_ENV', 'development')
        config_class_path = f'config.{app_env.capitalize()}Config'
        
        app.config.from_object(config_class_path)
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
    
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    try:
        upload_path = os.path.join(app.instance_path, app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_path, exist_ok=True) # Ensure exist_ok=True is set
        app.config['UPLOAD_PATH'] = upload_path # NEW: Store the full path for serving
    except OSError:
        pass
    
    # Initialize Flask-SQLAlchemy extension
    from .models.user_models import db
    db.init_app(app)
    
    # Import all models so SQLAlchemy knows about them
    from .models import user_models, docs_models  # noqa
    
    with app.app_context():
        db.create_all()
    
    # Register blueprints (UPDATED PATHS and REGISTRATION)
    from . import auth
    app.register_blueprint(auth.bp)
    
    # Blueprints from blueprints/roles
    from .blueprints.roles import admin 
    app.register_blueprint(admin.bp)
    from .blueprints.roles import worker 
    app.register_blueprint(worker.bp)
    from .blueprints.roles import planner 
    app.register_blueprint(planner.bp)
    from .blueprints.roles import client 
    app.register_blueprint(client.bp)

    # Blueprints from blueprints/artifacts
    from .blueprints.artifacts import tasks 
    app.register_blueprint(tasks.bp)
    from .blueprints.artifacts import forms 
    app.register_blueprint(forms.bp)
    from .blueprints.artifacts import users 
    app.register_blueprint(users.bp)
    from .blueprints.artifacts import plannings # <-- NEW REGISTRATION
    app.register_blueprint(plannings.bp) # <-- NEW REGISTRATION

    # ============================================================================
    # CRITICAL FIX: SERVE UPLOADED FILES FROM INSTANCE PATH
    # ============================================================================
    @app.route('/uploads/<path:filename>')
    def serve_uploaded_file(filename):
        # We serve the file directly from the instance/uploads path.
        # This handles the /uploads/uuid.ext URL structure used in the DB/Template.
        # Note: This is an insecure default; in production, Azure Blob Storage should handle this.
        return send_from_directory(
            app.config['UPLOAD_PATH'], 
            filename
        )
    
    # FIX DE SEGURIDAD: DESHABILITAR CACHÉ DEL NAVEGADOR (BFCACHE)
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
        
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        
        user = User.query.get(session["user_id"])
        
        if user is None:
            session.clear()
            return redirect(url_for("auth.login"))
        
        # Route based on user role (Using direct blueprint root URLs)
        if user.role == "admin":
            return redirect(url_for("admin.index"))
        elif user.role == "planner":
            return redirect(url_for("planner.index")) 
        elif user.role == "worker":
            return redirect(url_for("worker.index"))
        elif user.role == "client":
            return redirect(url_for("client.index")) 
        else:
            session.clear()
            return redirect(url_for("auth.login"))
    
    return app