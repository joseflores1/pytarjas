# config.py
"""
Configuration classes for different environments.

This module provides configuration classes for Development, Testing, and Production
environments. Each class inherits from a base Config class that defines common settings.

Usage in __init__.py:
    app.config.from_object('config.DevelopmentConfig')
    # or
    app.config.from_object('config.ProductionConfig')

The configuration can also be selected based on environment variables:
    config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(f'config.{config_name.capitalize()}Config')
"""

import os
from datetime import timedelta


class Config:
    """
    Base configuration class with settings common to all environments.
    
    This class defines default values that are shared across all environments.
    Environment-specific classes (Development, Testing, Production) inherit from
    this and override settings as needed.
    
    All settings can be overridden by environment variables defined in .env file.
    """
    
    # -------------------------------------------------------------------------
    # Flask Core Settings
    # -------------------------------------------------------------------------
    
    # Secret key for signing sessions, CSRF tokens, etc.
    # CRITICAL: Must be set in production, use a strong random value
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-please-change-in-production')
    
    # -------------------------------------------------------------------------
    # Database Settings (PostgreSQL with SQLAlchemy)
    # -------------------------------------------------------------------------
    
    # Database connection URI
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'SQLALCHEMY_DATABASE_URI',
        'postgresql://localhost/pytarjas'
    )
    
    # Disable Flask-SQLAlchemy event system (saves memory and overhead)
    # This system tracks changes to objects and emits signals
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Show SQL queries in console (useful for debugging)
    # Set to True in development to see what queries are being executed
    SQLALCHEMY_ECHO = False
    
    # SQLAlchemy engine options for connection pooling
    # Useful for production to manage database connections efficiently
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,          # Maximum number of connections to keep open
        'pool_recycle': 3600,     # Recycle connections after 1 hour
        'pool_pre_ping': True,    # Verify connections before using them
    }
    
    # -------------------------------------------------------------------------
    # Session Configuration (Security)
    # -------------------------------------------------------------------------
    
    # Session cookie settings for security
    SESSION_COOKIE_HTTPONLY = True      # Prevent JavaScript access (XSS protection)
    SESSION_COOKIE_SAMESITE = 'Lax'     # CSRF protection
    SESSION_COOKIE_SECURE = False       # Only send over HTTPS (set True in production)
    
    # Session lifetime (how long users stay logged in)
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)
    
    # -------------------------------------------------------------------------
    # Flask-WTF (Forms) Configuration
    # -------------------------------------------------------------------------
    
    # Enable CSRF protection for all forms
    WTF_CSRF_ENABLED = True
    
    # CSRF token expires after 1 hour
    WTF_CSRF_TIME_LIMIT = 3600
    
    # CSRF token field name (default is 'csrf_token')
    WTF_CSRF_FIELD_NAME = 'csrf_token'
    
    # -------------------------------------------------------------------------
    # File Upload Configuration (for field work attachments)
    # -------------------------------------------------------------------------
    
    # Maximum file size: 16MB (in bytes)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Upload folder (relative to instance folder)
    UPLOAD_FOLDER = 'uploads'
    
    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx'}
    
    # -------------------------------------------------------------------------
    # PWA Configuration (Progressive Web App)
    # -------------------------------------------------------------------------
    
    # Application name displayed when installed
    PWA_APP_NAME = os.getenv('PWA_APP_NAME', 'HGT Data Collector')
    
    # Short name for home screen icon
    PWA_SHORT_NAME = os.getenv('PWA_SHORT_NAME', 'HGT Collector')
    
    # Application description
    PWA_DESCRIPTION = os.getenv(
        'PWA_DESCRIPTION',
        'Aplicación para recolectar datos faenas en tiempo real'
    )
    
    # Theme color (browser UI color)
    PWA_THEME_COLOR = os.getenv('PWA_THEME_COLOR', '#2563eb')
    
    # Background color (splash screen)
    PWA_BACKGROUND_COLOR = os.getenv('PWA_BACKGROUND_COLOR', '#ffffff')
    
    # Service worker cache version
    # Increment this (v1 -> v2) when you update static files to force cache refresh
    SW_CACHE_VERSION = os.getenv('SW_CACHE_VERSION', 'v1')
    
    # Caching strategy: 'cache-first', 'network-first', or 'stale-while-revalidate'
    # cache-first: Best for offline-first apps (serves from cache, falls back to network)
    # network-first: Always tries network first (good for dynamic data)
    # stale-while-revalidate: Serves cache but updates in background
    SW_CACHE_STRATEGY = os.getenv('SW_CACHE_STRATEGY', 'cache-first')
    
    # Base URL of the application (used in PWA manifest)
    APP_BASE_URL = os.getenv('APP_BASE_URL', 'http://localhost:5000')
    
    # -------------------------------------------------------------------------
    # Logging Configuration
    # -------------------------------------------------------------------------
    
    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Log file path
    LOG_FILE = os.getenv('LOG_FILE', 'logs/pytarjas.log')
    
    # -------------------------------------------------------------------------
    # Email Configuration (optional - for notifications)
    # -------------------------------------------------------------------------
    
    # Email server settings (uncomment and configure if needed)
    # MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    # MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    # MAIL_USE_TLS = True
    # MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    # MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    # MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@pytarjas.com')


class DevelopmentConfig(Config):
    """
    Development environment configuration.
    
    Used when developing locally. Enables debug mode, detailed error pages,
    and SQL query logging for easier debugging.
    
    To use this config:
        export FLASK_ENV=development
        flask run
    """
    
    # Enable Flask debug mode
    # This provides:
    # - Interactive debugger in browser when errors occur
    # - Automatic reloading when code changes
    # - Detailed error pages
    # WARNING: Never enable in production - exposes sensitive information!
    DEBUG = True
    
    # Show SQL queries in console (helpful for debugging)
    SQLALCHEMY_ECHO = False 
    
    # Disable HTTPS requirement for session cookies (local development)
    SESSION_COOKIE_SECURE = False
    
    # Development-specific database (can override in .env)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'SQLALCHEMY_DATABASE_URI',
        'postgresql://josei:03e+_U#hS9AT@localhost:5432/pytarjas'
    )
    
    # Less strict session timeout for development
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


class TestingConfig(Config):
    """
    Testing environment configuration.
    
    Used during pytest runs. Disables CSRF protection for easier testing,
    uses a separate test database, and enables testing mode.
    
    This config is automatically applied by conftest.py fixtures.
    """
    
    # Enable Flask testing mode
    # This disables error catching during request handling so you get
    # better error reports when performing test requests
    TESTING = True
    
    # Disable CSRF protection for easier testing
    # In tests, you don't want to deal with CSRF tokens
    WTF_CSRF_ENABLED = False
    
    # Use separate test database
    # CRITICAL: Never use production database for tests!
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'TEST_DATABASE_URI',
        'postgresql://josei:03e+_U#hS9AT@localhost:5432/pytarjas_test'
    )
    
    # Don't show SQL in tests (cleaner test output)
    SQLALCHEMY_ECHO = False
    
    # Use a simple secret key for testing
    SECRET_KEY = 'testing-secret-key-not-secure'
    
    # Faster password hashing in tests (bcrypt rounds)
    # Note: This requires Flask-Bcrypt configuration
    # BCRYPT_LOG_ROUNDS = 4


class ProductionConfig(Config):
    """
    Production environment configuration.
    
    Used when deployed to production server. Enforces security settings,
    disables debug mode, and uses production-grade settings.
    
    To use this config:
        export FLASK_ENV=production
        gunicorn "pytarjas:create_app()" --bind 0.0.0.0:8000
    
    IMPORTANT: Before deploying to production:
    1. Set a strong SECRET_KEY in environment
    2. Configure production database URI
    3. Set SESSION_COOKIE_SECURE=True (requires HTTPS)
    4. Configure proper logging
    5. Set up database backups
    """
    
    # Disable debug mode (CRITICAL for security)
    DEBUG = False
    
    # Disable SQL query logging (reduces overhead)
    SQLALCHEMY_ECHO = False
    
    # Require HTTPS for session cookies (REQUIRES SSL/TLS)
    # Only enable this when you have HTTPS configured!
    SESSION_COOKIE_SECURE = True
    
    # Production database should be set via environment variable
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'SQLALCHEMY_DATABASE_URI',
        # No default - force explicit configuration in production
    )
    
    # Stricter session timeout in production (4 hours)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)
    
    # Production error logging
    LOG_LEVEL = 'WARNING'


# Dictionary for easy config selection
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str =None) -> (
        DevelopmentConfig | TestingConfig | ProductionConfig):
    """
    Get configuration class based on name.
    
    Args:
        config_name: Name of config ('development', 'testing', 'production')
                    If None, uses FLASK_ENV environment variable
    
    Returns:
        Configuration class
        
    Example:
        config_class = get_config('production')
        app.config.from_object(config_class)
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    return config.get(config_name, DevelopmentConfig)