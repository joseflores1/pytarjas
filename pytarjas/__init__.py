# pytarjas/__init__.py
import os
from dotenv import load_dotenv
from flask import Flask

# Load environment variables
load_dotenv()


def create_app(test_config=None):
    """
    Create and configure the Flask application.
    
    Args:
        test_config: Optional dictionary of configuration values for testing
        
    Returns:
        Flask: Configured Flask application instance
    """
    # Create Flask app
    app = Flask(__name__, instance_relative_config=True)
    
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=os.getenv("SQLALCHEMY_DATABASE_URI"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ECHO=False,  # Set to True for SQL query debugging
    )
    
    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Initialize extensions
    from .models.user_models import db
    db.init_app(app)
    
    # Import all models so SQLAlchemy knows about them
    # This MUST happen after db.init_app() but before db.create_all()
    from .models import user_models, docs_models #noqa

    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Register blueprints (when ready)
    # from . import auth
    # app.register_blueprint(auth.bp)
    
    # from . import blog
    # app.register_blueprint(blog.bp)
    # app.add_url_rule("/", endpoint="index")
    
    return app