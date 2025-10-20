# user_models.py
"""
Database models for the Pytarjas application.

This module defines the user model hierarchy using SQLAlchemy's polymorphic inheritance.
All user types (Admin, Worker, Planner, Client) inherit from the base User class.

The models are designed to work with PostgreSQL and use UUID for primary keys.
"""

import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

# Initialize SQLAlchemy with the custom base class
db = SQLAlchemy(model_class=Base)

class User(db.Model):
    """
    Base user class with polymorphic inheritance.
    
    This class defines the common attributes and methods shared by all user types.
    Different user roles (Admin, Worker, Planner, Client) inherit from this class.
    
    Attributes:
        id: Unique identifier (UUID as string)
        username: Unique username for authentication
        password_hash: Hashed password (never store plain passwords)
        email: User's email address (unique)
        role: User role/type (used for polymorphic identity)
        created_at: Timestamp when user was created
        updated_at: Timestamp of last update
        login_at: Timestamp of last login
    """

    # Set the table name to: user
    __tablename__="users"

    # Primary key - using UUID as string for PostgreSQL compatibility
    id: Mapped[str]= mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Authentication fields
    username: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True, # Index for faster lookups during authentication
    )
    password_hash: Mapped[str]= mapped_column(
        String(255),
        unique=False,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
        index=True,
    )

    # Role field for polymorphic inheritance
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Timestamp fields 
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    login_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Polymorphic configuration - enables inheritance
    __mapper_args__={
        "polymorphic_identity": "users",
        "polymorphic_on": role,
    }

    # Password methods
    def check_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)

    def reset_password(self, new_password: str) -> None:
        """
        Reset password without requiring the old password.
        
        This method is typically used by administrators or for password
        recovery flows. Updates the updated_at timestamp.
        
        Args:
            new_password: New plain text password to set
        """
        self.password_hash=generate_password_hash(new_password)
        self.updated_at=datetime.now(timezone.utc)

    def change_password(self, old_password: str, new_password: str) -> bool:
        """
        Change password if the old password is correct.
        
        This method requires verification of the current password before
        allowing the change. Updates the updated_at timestamp on success.
        
        Args:
            old_password: Current password for verification
            new_password: New password to set
            
        Returns:
            True if password was changed successfully, False if old password
            was incorrect
        """
        if check_password_hash(self.password_hash, old_password):
            self.password_hash=generate_password_hash(new_password)
            self.updated_at=datetime.now(timezone.utc)
            return True
        return False

    def update_login_time(self) -> None:
        """
        Update the last login timestamp to the current time.
        
        Should be called after successful authentication.
        """
        self.login_at=datetime.now(timezone.utc)

    def __repr__(self):
        """String representation for debugging"""
        return f"<User: {self.username} ({self.role})>"


class Admin(User):
    """
    Administrator user with elevated privileges.
    
    Admins can:
    - Create and manage other users
    - Access all system functions
    - Configure system settings
    - View all tarjas and reports
    """
    __mapper_args__ = {
        "polymorphic_identity": "admin",
    }
    def set_user_password(self, user: User, password: str) -> None:
        """
        Hash and set the user's password.
        
        Uses werkzeug.security password hashing (scrypt method with a salt) which is secure
        and resistant to brute-force attacks.
        
        Args:
            password: Plain text password to hash and store
        """
        user.password_hash=generate_password_hash(password)
        if user.created_at:
            user.updated_at=datetime.now(timezone.utc)

    def update_user_info(
            self, user: User, new_email: str | None = None, new_username: str | None = None,
            new_role: str | None = None,
    ) -> None:
        """
        Update user profile information.
        
        Only updates fields that are provided (not None).
        Updates the updated_at timestamp.
        In the future, may add more Args if needed.
        
        Args:
            user: User whose information will be updated
            new_email: New email address (optional)
            new_username: New username (optional)
            new_role: New role (optional)
        """
        if new_email:
            user.email=new_email
        if new_username:
            user.username=new_username
        if new_role:
            user.role=new_role
        if new_email or new_username or new_role:
            user.updated_at=datetime.now(timezone.utc)

    def create_user(
            self,
            username: str,
            email: str,
            password: str,
            role: str,
    ) -> User:
        """
        Factory method to create a new user of any type.
        
        This method handles the creation of users with different roles,
        instantiating the appropriate subclass based on the role parameter.
        
        Args:
            username: Username for the new user
            email: Email address for the new user
            password: Plain text password (will be hashed)
            role: User role ('admin', 'worker', 'planner', or 'client')
            
        Returns:
            New user instance of the appropriate type
            
        Example:
            admin = Admin.query.first()
            new_worker = admin.create_user(
                username="john_doe",
                email="john@example.com",
                password="secure_password",
                role="worker"
            )
            db.session.add(new_worker)
            db.session.commit()
        """
        user_classes = {
            "admin": Admin,
            "worker": Worker,
            "planner": Planner,
            "client": Client,
        }

        user_class=user_classes.get(role, User)

        user = user_class(
            username=username,
            email=email,
            role=role,
        )
        self.set_user_password(user, password)
        user.created_at=datetime.now(timezone.utc)
        return user

    def __repr__(self):
        return f"<Admin: {self.username}>"

class Worker(User):
    """
    Field worker (tarjador) who performs tarja operations.
    
    Workers:
    - Perform consolidation and deconsolidation of containers
    - Fill out tarja forms during faenas
    - Take photographs of containers and cargo
    - Use tablets in the field to record information
    - Can work offline and sync when connectivity is restored
    """
    __mapper_args__={
        "polymorphic_identity": "worker",
    }

    def __repr__(self):
        """String representation for debugging"""
        return f"<Worker: {self.username}>"

class Planner(User):
    """
    Coordinator/planner who manages work assignments.
    
    Planners:
    - Receive work schedules from Customer Service or clients
    - Assign containers and tasks to workers
    - Review completed tarjas for accuracy
    - Handle seal verification discrepancies
    - Coordinate with IT Support for tarja corrections
    - Download and send tarjas to clients
    """
    __mapper_args__={
        "polymorphic_identity": "planner",
    }


    def __repr__(self):
        """String representation for debugging"""
        return f"<Planner: {self.username}>"
    

class Client(User):
    """
    External client who receives tarja reports.
    
    Clients:
    - View their own tarjas and reports
    - Download tarja PDFs
    - Track container operations
    - Have read-only access to their data
    - Cannot modify system data
    """
    __mapper_args__={
        "polymorphic_identity": "client",
    }

    def __repr__(self):
        """String representation for debugging"""
        return f"<Client: {self.username}>"
 