# docs_models.py
"""
Document and form management models for the Pytarjas application.

This module defines models for managing forms, planifications, records, and documents
used in the consolidation/deconsolidation tarja process.

The workflow is:
1. Planner creates a Planification and associates it with a Form
2. System creates Records (one per row/entry in the planification)
3. System auto-generates Documents (one per Record, based on the Form)
4. Workers fill Documents during faenas
5. System generates PDF tarjas from completed Documents
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.attributes import flag_modified
from .user_models import db, User

class Form(db.Model):
    """
    Predefined questionnaire template for tarjas.
    
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

    id: Mapped[str]=mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

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
        index=True,
    )

    is_active: Mapped[bool]=mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime]=mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None]=mapped_column(
        DateTime,
        nullable=True,
    )

    questions: Mapped[list["Question"]]=relationship(
        "Question",
        back_populates="form",
        cascade="all, delete-orphan",
    )
    planifications: Mapped[list["Planification"]]=relationship(
        "Planification",
        back_populates="form"
    )

class Question(db.Model):
    """
    Individual question/field within a Form.
    
    Attributes:
        id: Unique identifier (UUID)
        form_id: Foreign key to parent Form
        question_text: The question to display to the worker
        question_type: Type of input (text, number, photo, date, boolean, select)
        is_required: Whether this question must be answered
        order: Display order within the form (lower numbers first)
        options: JSON field for select/radio options, validation rules, etc.
        created_at: When the question was created
        updated_at: Last modification timestamp
        form: Related Form object (many-to-one)
    """

    __tablename__="question"

    id: Mapped[str]=mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    form_id: Mapped[str]=mapped_column(
        String(36),
        ForeignKey("form.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    question_text: Mapped[str]=mapped_column(
        String(500),
        nullable=False,
    )
    question_type: Mapped[str]=mapped_column(
        String(50),
        nullable=False,
    )
    is_required: Mapped[bool]=mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    order: Mapped[int]=mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    options: Mapped[dict | None]=mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime]=mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None]=mapped_column(
        DateTime,
        nullable=True,
    )
        
    form: Mapped["Form"]=relationship(
        "Form",
        back_populates="questions",
    )

    def __repr__(self):
        return f"<Question: {self.question_text[:50]}... ({self.question_type})>"        

class Planification(db.Model):
    """
    Work planning document created by Planner.
    
    Attributes:
        id: Unique identifier (UUID)
        planner_id: Foreign key to User (Planner who created it)
        form_id: Foreign key to Form (template to use for documents)
        file_path: Location of uploaded file - empty if created via UI
        file_name: Original filename - empty if created via UI
        status: Processing status (uploaded, processing, completed, error)
        client_name: Client who requested this work
        total_records: Number of records/rows in this planification
        created_at: When the planification was created
        updated_at: Last modification timestamp
        planner: Related User (Planner) object (many-to-one)
        form: Related Form object (many-to-one)
        records: Related Record objects (one-to-many)
    """

    __tablename__="planification"

    id: Mapped[str]=mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    planner_id: Mapped[str]=mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
 
    form_id: Mapped[str]=mapped_column(
        String(36),
        ForeignKey("form.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    file_path: Mapped[str]=mapped_column(
        String(255),
        nullable=False,
        default="",
    )
    file_name: Mapped[str]=mapped_column(
        String(255),
        nullable=False,
        default="",
    )

    status: Mapped[str]=mapped_column(
        String(50),
        nullable=False,
        default="uploaded",
        index=True,
    )

    client_name: Mapped[str | None]=mapped_column(
        String(200),
        nullable=True,
        index=True,
    )
    
    total_records: Mapped[int]=mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime]=mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None]=mapped_column(
        DateTime,
        nullable=True,
    )

    planner: Mapped["User"]=relationship(
        "User",
        foreign_keys=[planner_id],
    )
    form: Mapped["Form"]=relationship(
        "Form",
        back_populates="planifications",
    )
    records: Mapped[list["Record"]]=relationship(
        "Record",
        back_populates="planification",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Planification: {self.client_name} - {self.total_records} records>"


class Record(db.Model):
    """
    Single work item (row) from a Planification.
    
    Uses JSON to store all form-specific data, allowing different forms
    to have different fields without requiring database migrations.
    
    Attributes:
        id: Unique identifier (UUID) - the primary key
        planification_id: Foreign key to parent Planification
        record_data: JSON containing all form-specific fields
        created_at: When the record was created
        updated_at: When the record was last modified
        planification: Related Planification object (many-to-one)
        document: Related Document object (one-to-one)
    
    Example record_data for different forms:
        Container form: {"container_number": "ABCD123", "ship_name": "MSC Luna", ...}
        Pallet form: {"pallet_number": "PLT-001", "warehouse": "A-15", ...}
        Booking form: {"booking_number": "BK2025001", "client": "ACME", ...}
    """
    
    __tablename__ = "record"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    planification_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("planification.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    record_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    
    planification: Mapped["Planification"] = relationship(
        "Planification",
        back_populates="records",
    )
    
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="record",
        uselist=False,
        cascade="all, delete-orphan",
    )
    
    def get_field(self, field_name: str, default=None):
        """Get a field from record_data with optional default value."""
        return self.record_data.get(field_name, default)
    
    def set_field(self, field_name: str, value):
        """Set a field in record_data and mark as modified."""
        self.record_data[field_name] = value
        flag_modified(self, 'record_data')
        self.updated_at = datetime.now(timezone.utc)
    
    def update_fields(self, fields_dict: dict):
        """Update multiple fields in record_data at once."""
        self.record_data.update(fields_dict)
        flag_modified(self, 'record_data')
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"<Record: {self.id}>"


class Document(db.Model):
    """
    Fillable tarja document for Workers.
    
    Documents are automatically created from Records and Forms.
    Workers fill them during faenas by answering questions and taking photos.
    
    Attributes:
        id: Unique identifier (UUID)
        record_id: Foreign key to Record (unique for one-to-one)
        worker_id: Foreign key to User (Worker who fills it)
        status: Document status (pending, in_progress, completed, reviewed, approved)
        responses: JSON storing all question answers
        photos: JSON array of photo file paths/URLs
        pdf_path: Path to generated PDF tarja
        started_at: When worker started filling the document
        completed_at: When worker finished filling the document
        reviewed_at: When planner reviewed the document
        synced_at: When offline data was synced to server
        is_synced: Whether offline changes are synced
        created_at: When the document was created
        updated_at: Last modification timestamp
        record: Related Record object (one-to-one)
        worker: Related User (Worker) object (many-to-one)
    """
    __tablename__ = "document"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("record.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    worker_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )
    
    responses: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    photos: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    pdf_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    is_synced: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    
    record: Mapped["Record"] = relationship(
        "Record",
        back_populates="document",
    )
    worker: Mapped["User"] = relationship(
        "User",
        foreign_keys=[worker_id],
    )
    
    def start_filling(self, worker_id: str) -> None:
        """Mark document as started by a worker."""
        self.worker_id = worker_id
        self.status = "in_progress"
        self.started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def complete_filling(self) -> None:
        """Mark document as completed by the worker."""
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_reviewed(self) -> None:
        """Mark document as reviewed by a planner."""
        self.status = "reviewed"
        self.reviewed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_synced(self) -> None:
        """Mark document as synced after offline changes."""
        self.is_synced = True
        self.synced_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"<Document: {self.id} ({self.status})>"