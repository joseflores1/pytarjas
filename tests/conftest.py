# tests/conftest.py
"""
Pytest configuration and fixtures for testing.

This module provides core fixtures for the test suite:
- app: Flask application instance with test configuration
- _db: Database with transaction-based test isolation
- client: Flask test client for HTTP requests
- runner: Flask CLI test runner
- session: Database session for direct database operations
- auth_actions: Helper class for authentication testing
"""

import os
import pytest
from sqlalchemy.orm import scoped_session, sessionmaker
from pytarjas import create_app
from pytarjas.models.user_models import db


@pytest.fixture(scope="session")
def app():
    """
    Create and configure a Flask application instance for testing.
    
    Scope: session - Created once for the entire test session
    
    This fixture:
    1. Sets up test environment variables
    2. Creates the Flask app with test configuration
    3. Creates all database tables before tests
    4. Drops all tables after tests complete
    
    Returns:
        Flask: Configured Flask application instance
        
    Note: Uses PostgreSQL for testing. Ensure your TEST_DATABASE_URI
    environment variable points to a test database, not production!
    """
    # Set test environment - prevents accidental use of production configs
    os.environ['FLASK_ENV'] = 'testing'
    
    # Test configuration
    # CRITICAL: Make sure this points to a TEST database, never production!
    test_config = {
        "TESTING": True,  # Enables Flask testing mode
        "SQLALCHEMY_DATABASE_URI": os.getenv(
            "TEST_DATABASE_URI",
            "postgresql://user:pass@localhost/test_db"  # Default test DB
        ),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,  # Disable event system (saves memory)
        "SECRET_KEY": "testing-12345",  # Insecure key OK for testing
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for easier testing
    }
    
    # Create the app with test configuration
    app = create_app(test_config)
    
    yield app  # Tests run here
    
    # Cleanup after ALL tests complete
    with app.app_context():
        db.session.remove()  # Close all sessions
        db.drop_all()  # Drop all tables - clean slate for next test run


@pytest.fixture(scope="function", autouse=False)
def _db(app):
    """
    Provide database instance with transaction-based test isolation.
    
    Scope: function - Creates a new transaction for EACH test
    
    How it works:
    1. Opens a database connection
    2. Starts a transaction (BEGIN)
    3. Binds the SQLAlchemy session to this transaction
    4. Test runs (any DB operations happen in the transaction)
    5. Transaction is rolled back (ROLLBACK) - undoing all changes
    6. Connection is closed
    
    This ensures each test starts with a clean database state without
    needing to recreate tables (which is slow).
    
    Returns:
        SQLAlchemy: Database instance bound to a transaction
        
    Note: The rollback happens automatically after each test, so tests
    don't interfere with each other.
    """
    with app.app_context():
        # Create a new database connection for this test
        connection = db.engine.connect()
        
        # Begin a transaction (all subsequent DB operations will be part of this)
        transaction = connection.begin() #noqa
         
        # Create a session factory bound to this connection
        # sessionmaker creates a factory for Session objects
        session_factory = sessionmaker(bind=connection)
        
        # Create a scoped session (thread-local session)
        # This ensures all code in this test uses the same session
        session = scoped_session(session_factory)
        
        # Replace the global db.session with our transaction-bound session
        # This is the key: now all db.session.add(), commit(), etc. use our transaction
        db.session = session
        
        yield db  # Test runs here
        
        # Cleanup: Undo everything the test did
        session.remove()  # Close the session
        connection.close()  # Close the connection


@pytest.fixture
def client(app):
    """
    Provide a Flask test client for making HTTP requests.
    
    This client allows you to:
    - Make GET, POST, PUT, DELETE requests
    - Test routes and endpoints
    - Simulate browser behavior
    
    Example usage:
        def test_homepage(client):
            response = client.get('/')
            assert response.status_code == 200
    
    Returns:
        FlaskClient: Test client for making requests
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    Provide a Flask CLI test runner for testing CLI commands.
    
    Useful for testing:
    - Custom Flask CLI commands
    - Database initialization commands
    - Management scripts
    
    Example usage:
        def test_init_db_command(runner):
            result = runner.invoke(args=['init-db'])
            assert 'Initialized' in result.output
    
    Returns:
        FlaskCliRunner: CLI test runner
    """
    return app.test_cli_runner()


@pytest.fixture
def session(app, _db):
    """
    Provide a database session for direct database operations.
    
    Use this when you need to:
    - Query the database directly in tests
    - Verify that data was saved correctly
    - Set up test data
    
    Example usage:
        def test_user_creation(session):
            user = User(username="test")
            session.add(user)
            session.commit()
            assert User.query.first() is not None
    
    Returns:
        Session: SQLAlchemy session for database operations
        
    Note: This session is part of the transaction managed by _db,
    so all changes will be rolled back after the test.
    """
    with app.app_context():
        yield _db.session


@pytest.fixture
def auth_actions(client):
    """
    Provide authentication helper methods for testing auth flows.
    
    This fixture creates a helper class that makes it easy to:
    - Log users in and out during tests
    - Test authentication-protected routes
    - Simulate user sessions
    
    Example usage:
        def test_logout(client, auth_actions):
            auth_actions.login()
            auth_actions.logout()
            # Verify user is logged out
    
    Returns:
        AuthActions: Helper class with login() and logout() methods
    """
    class AuthActions:
        """Helper class for authentication operations in tests."""
        
        def __init__(self, client):
            """
            Initialize with a test client.
            
            Args:
                client: Flask test client for making requests
            """
            self._client = client
        
        def login(self, username="test", password="test"):
            """
            Log in a user by posting to the login endpoint.
            
            Args:
                username: Username to log in with (default: "test")
                password: Password to log in with (default: "test")
            
            Returns:
                Response: The response from the login request
            """
            return self._client.post(
                "/auth/login",
                data={"username": username, "password": password},
            )
        
        def logout(self):
            """
            Log out the current user by getting the logout endpoint.
            
            Returns:
                Response: The response from the logout request
            """
            return self._client.get("/auth/logout")
    
    return AuthActions(client)