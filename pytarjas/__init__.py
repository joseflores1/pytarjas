# pytarjas/__init__.py
import os
from flask import Flask


def create_app(test_config=None):
    """
    Create and configure the Flask application.
    
    This is the application factory pattern recommended by Flask.
    It allows creating multiple instances of the app with different
    configurations (useful for testing, development, production).
    
    Args:
        test_config: Optional dictionary of configuration values for testing.
                     When provided, overrides all other configuration.
        
    Returns:
        Flask: Configured Flask application instance
        
    Example:
        # Development (default - no environment variables needed)
        app = create_app()
        
        # Production (set APP_ENV in .env or environment)
        # APP_ENV=production
        app = create_app()
        
        # Testing (used by pytest)
        app = create_app({"TESTING": True})
    """
    # Create Flask app instance
    # instance_relative_config=True tells Flask to look for config files
    # in the instance folder (for deployment-specific settings)
    app = Flask(__name__, instance_relative_config=True)
    
    if test_config is None:
        # Load configuration from config.py based on APP_ENV
        # Default to 'development' if APP_ENV is not set
        # You can set APP_ENV in your .env file: APP_ENV=production
        app_env = os.getenv('APP_ENV', 'development')
        
        # Load the appropriate config class
        # 'development' -> DevelopmentConfig
        # 'production' -> ProductionConfig  
        # 'testing' -> TestingConfig
        config_class = f'config.{app_env.capitalize()}Config'
        app.config.from_object(config_class)
        
        # Optional: Load instance-specific config file if it exists
        # This allows overriding config.py settings on a per-deployment basis
        # silent=True means don't error if the file doesn't exist
        app.config.from_pyfile('config.py', silent=True)
        
    else:
        # Load the test config if passed in (for pytest)
        # This completely overrides config.py settings
        app.config.from_mapping(test_config)
    
    # Ensure the instance folder exists
    # This folder stores deployment-specific files (logs, uploads, etc.)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Ensure upload folder exists (for field work file attachments)
    try:
        upload_path = os.path.join(app.instance_path, app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_path)
    except OSError:
        pass
    
    # Initialize Flask-SQLAlchemy extension
    from .models.user_models import db
    db.init_app(app)
    
    # Import all models so SQLAlchemy knows about them
    # This MUST happen after db.init_app() but before db.create_all()
    # noqa tells linters to ignore "unused import" warnings
    from .models import user_models, docs_models  # noqa
    
    # Create database tables if they don't exist
    # In production, use Flask-Migrate instead of db.create_all()
    with app.app_context():
        db.create_all()
    
    # Register blueprints
    from . import auth
    app.register_blueprint(auth.bp)
    
    from . import admin
    app.register_blueprint(admin.bp)
    # from . import blog
    # app.register_blueprint(blog.bp)
    # app.add_url_rule("/", endpoint="index")
    
    # TODO: Register PWA routes (manifest.json, service-worker.js)
    # We'll add these in the next step
    
    return app