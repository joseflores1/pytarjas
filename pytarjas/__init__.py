# pytarjas/__init__.py
import os
import logging
from flask import Flask, redirect, url_for, session, send_from_directory
from dotenv import load_dotenv
from .models.user_models import User

# Configure logging for Azure and Local environments
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(test_config=None):
    """
    Create and configure the Flask application.
    """
    # -------------------------------------------------------------------------
    # Environment Configuration
    # -------------------------------------------------------------------------
    
    # Define the base directory (project root)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Explicitly load .env.development if it exists to override standard .env
    # This is critical for local development to prevent picking up production vars
    dev_env = os.path.join(base_dir, '.env.development')
    if os.path.exists(dev_env):
        load_dotenv(dev_env, override=True)
        logger.info("Loaded configuration from .env.development")

    # Create Flask app instance
    app = Flask(__name__, instance_relative_config=True)
    
    if test_config is None:
        # Check both FLASK_ENV and APP_ENV to be safe in Azure
        # Priority: FLASK_ENV > APP_ENV > development
        app_env = os.getenv('FLASK_ENV') or os.getenv('APP_ENV') or 'development'
        config_class_path = f'config.{app_env.capitalize()}Config'
        
        try:
            app.config.from_object(config_class_path)
            # Load additional settings from instance/config.py if it exists
            app.config.from_pyfile('config.py', silent=True)
            logger.info(f"Application starting in {app_env} mode.")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            
    else:
        app.config.from_mapping(test_config)
    
    # Ensure the instance path exists for local storage/uploads
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Configure upload paths
    try:
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        upload_path = os.path.join(app.instance_path, upload_folder)
        os.makedirs(upload_path, exist_ok=True)
        app.config['UPLOAD_PATH'] = upload_path
    except OSError:
        pass
    
    # Initialize Flask-SQLAlchemy extension
    from .models.user_models import db
    db.init_app(app)
    
    # Import all models so SQLAlchemy knows about them
    from .models import user_models, docs_models  # noqa
    
    with app.app_context():
        try:
            # Attempt to create tables. The DB must already exist.
            db.create_all()
            logger.info("Database synchronization complete.")
        except Exception as e:
            logger.error("Critical: Could not connect to the database.")
            # Masking password for safety in logs
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if '@' in db_uri:
                logger.error(f"Target Database Host: {db_uri.split('@')[-1]}")
            
            raise e
    
    # Register blueprints
    from . import auth
    app.register_blueprint(auth.bp)
    
    from .blueprints.roles import admin, worker, planner, client
    app.register_blueprint(admin.bp)
    app.register_blueprint(worker.bp)
    app.register_blueprint(planner.bp)
    app.register_blueprint(client.bp)

    from .blueprints.artifacts import tasks, forms, users, plannings
    app.register_blueprint(tasks.bp)
    app.register_blueprint(forms.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(plannings.bp)

    # ============================================================================
    # SERVE UPLOADED FILES FROM INSTANCE PATH
    # ============================================================================
    @app.route('/uploads/<path:filename>')
    def serve_uploaded_file(filename):
        """Serves files from the local instance upload directory."""
        return send_from_directory(
            app.config['UPLOAD_PATH'], 
            filename
        )
    
    # Security: Disable Browser Cache (BFCACHE)
    @app.after_request
    def set_secure_headers(response):
        """Adds headers to prevent page caching by the browser."""
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # ============================================================================
    # ROOT ROUTE: Redirect to appropriate page based on authentication
    # ============================================================================
    @app.route("/")
    def index():
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        
        user = User.query.get(session["user_id"])
        
        if user is None:
            session.clear()
            return redirect(url_for("auth.login"))
        
        # Route based on user role
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