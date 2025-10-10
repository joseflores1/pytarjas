# docs_models.py
"""
Document and form management models for the Pytarjas application.

This module defines models for managing forms, planifications, records, and documents
used in the consolidation/deconsolidation tarja process.

The workflow is:
1. Planner uploads a Planification and associates it with a Form
2. System creates Records (one per row in the planification)
3. System auto-generates Documents (one per Record, based on the Form)
4. Workers fill Documents during faenas
5. System generates PDF tarjas from completed Documents
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .user_models import db

class Form(db.Model):
    """
    Predefined questionnaire template for tarjas.
    
    Forms are reusable templates that define what questions workers must answer
    during consolidation/deconsolidation operations. Examples include:
    - Desconsolidado Form
    - Consolidado Form  
    - Seal Verification Form
    
    Attributes:
        id: Unique identifier (UUID)
        name: Form name (e.g., "Formulario de Desconsolidado")
        description: Detailed description of the form's purpose
        form_type: Type category (consolidado, desconsolidado, seal_verification)
        is_active: Whether this form is currently available for use
        created_at: When the form was created
        updated_at: Last modification timestamp
        questions: Related Question objects (one-to-many)
        planifications: Planifications using this form (one-to-many)
    """
    __tablename__="form"

    # Primary key
    id: Mapped[str]=mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Form metadata
    name: Mapped[str]=mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    description: Mapped[str | None]=mapped_column(
        Text,
        nullable=True,
    )
    form_type: Mapped[str]=mapped_column(
        String(50),
        nullable=True,
        index=True # For filtering rows by type
    )

    # Form status
    is_active: Mapped[bool]=mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Timestamps
    created_at: Mapped[datetime]=mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime]=mapped_column(
        DateTime,
        nullable=True,
    )

    # Relationships
    questions: Mapped[list["Question"]]=relationship(
        "Question",
        back_populates="form",
        cascade="all, delete-orphan" # Delete questions when the form is deleted
    )

class Question(db.Model):