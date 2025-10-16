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
from .user_models import db, User

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
    planifications: Mapped[list["Planification"]]=relationship(
        "Planification",
        back_populates="form"
    )

class Question(db.Model):
    """
    Individual question/field within a Form.
    
    Questions define what data workers must capture during faenas.
    They can be different types (text, number, photo, etc.) and may have
    validation rules.
    
    Attributes:
        id: Unique identifier (UUID)
        form_id: Foreign key to parent Form
        question_text: The question to display to the worker
        question_type: Type of input (text, number, photo, date, boolean, select)
        is_required: Whether this question must be answered
        order: Display order within the form (lower numbers first)
        options: JSON field for select/radio options, validation rules, etc.
        created_at: When the question was created
        form: Related Form object (many-to-one)
    """

    __tablename_="question"

    # Primary key
    id: Mapped[str]=mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Foreign key to Form
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
        #Valid types: text, number, photo, date, datetime, boolean, select, textarea
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

    # JSON field for additional config
    # Can store: validation rules, select options, placeholders, help text, etc.
    options: Mapped[dict | None]=mapped_column(
        JSON,
        nullable=True,
    )

    # Timestamp
    created_at: Mapped[datetime]=mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime]=mapped_column(
        DateTime,
        nullable=True,
    )
        
    # Relationship
    form: Mapped["Form"]=relationship(
        "Form",
        back_populates="questions",
    )

    def __repr__(self):
        return f"<Question: {self.question_text[:50]}... ({self.question_type})>"        

class Planification(db.Model):
    """
    Work planning document uploaded by Planner.
    
    Planifications contain the schedule of containers to be processed.
    They are typically Excel files uploaded by planners, with each row
    becoming a Record (work item) that generates a Document to be filled.
    
    Attributes:
        id: Unique identifier (UUID)
        planner_id: Foreign key to User (Planner who uploaded it)
        form_id: Foreign key to Form (template to use for documents)
        file_path: Location of uploaded file (Excel, CSV, etc.)
        file_name: Original filename
        status: Processing status (uploaded, processing, completed, error)
        client_name: Client who requested this work (string for now)
        total_records: Number of records/rows in this planification
        created_at: When the planification was uploaded
        updated_at: Last modification timestamp
        planner: Related User (Planner) object (many-to-one)
        form: Related Form object (many-to-one)
        records: Related Record objects (one-to-many)
    """

    __tablename__="planification"

    # Primary key
    id: Mapped[str]=mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

   # Foreign keys
    planner_id: Mapped[str]=mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
 
    form_id: Mapped[str]=mapped_column(
        String(36),
        ForeignKey("form.id", ondelete="RESTRICT"), # Dont delete if form is deleted
        nullable=False,
        index=True,
    )

    # File information
    file_path: Mapped[str]= mapped_column(
        String(255),
        nullable=False,
    )
    file_name: Mapped[str]=mapped_column(
        String(255),
        nullable=False,
    )

    # Status tracking
    status: Mapped[str]=mapped_column(
        String(50),
        nullable=False,
        default="uploaded",
        index=True,
    )
        # Valid statuses: uploaded, processing completed, error

    # Client information (as string for now)
    client_name: Mapped[str | None]=mapped_column(
        String(200),
        nullable=True,
        index=True, # For filtering by client
    )
    
    # Metadata
    total_records: Mapped[int]=mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Timestamps
    created_at: Mapped[datetime]=mapped_column(
        DateTime,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )
    updated_at: Mapped[datetime]=mapped_column(
        DateTime,
        nullable=True,
    )

    # Relationships
    planner: Mapped["User"]=relationship(
        "User",
        foreign_keys=[planner_id]
    )
    form: Mapped["Form"]=relationship(
        "Form",
        back_populates="planifications",
    )
    records: Mapped[list["Record"]]=relationship(
        "Record",
        back_populates="planification"
    )

class Record(db.Model):
     """
    Single work item (row) from a Planification.
    
    Each Record represents one container operation to be documented.
    It contains the basic container and shipment information, and
    automatically generates one Document for the worker to fill.
    
    Attributes:
        id: Unique identifier (UUID)
        planification_id: Foreign key to parent Planification
        container_number: Container identification number
        client_name: Client associated with this container
        ship_name: Name of the ship (Nave)
        voyage_stage: Voyage/Stage information (Viaje/Etapa)
        reservation: Reservation number
        origin: Origin port/location
        destination: Destination port/location
        seal_number: Container seal number
        iso_code: ISO container code (e.g., 40HC, 20GP)
        manifested_packages: Expected number of packages (for desconsolidado)
        weight_kg: Weight in kilograms
        size: Container size (e.g., 20, 40)
        additional_data: JSON for any extra fields
        created_at: When the record was created
        planification: Related Planification object (many-to-one)
        document: Related Document object (one-to-one)
    """  
     __tablename__ = "record"

      # Primary key
     id: Mapped[str] = mapped_column(
         String(36),
         primary_key=True,
         default=lambda: str(uuid.uuid4()),
     )
    
     # Foreign key to Planification
     planification_id: Mapped[str] = mapped_column(
         String(36),
         ForeignKey("planification.id", ondelete="CASCADE"),
         nullable=False,
         index=True,
     )
    
     # Container and shipment information
     container_number: Mapped[str] = mapped_column(
         String(50),
         nullable=False,
         index=True,  # Frequently searched
     )
     client_name: Mapped[str | None] = mapped_column(
         String(200),
         nullable=True,
         index=True,
     )
     ship_name: Mapped[str | None] = mapped_column(
         String(200),
         nullable=True,
     )
     voyage_stage: Mapped[str | None] = mapped_column(
         String(100),
         nullable=True,
     )
     reservation: Mapped[str | None] = mapped_column(
         String(100),
         nullable=True,
     )
     origin: Mapped[str | None] = mapped_column(
         String(200),
         nullable=True,
     )
     destination: Mapped[str | None] = mapped_column(
         String(200),
         nullable=True,
     )
     seal_number: Mapped[str | None] = mapped_column(
         String(100),
         nullable=True,
     )
     iso_code: Mapped[str | None] = mapped_column(
         String(100),
         nullable=True,
     )
     manifested_packages: Mapped[int | None] = mapped_column(
         Integer,
         nullable=True,
     )
     weight_kg: Mapped[float | None] = mapped_column(
         nullable=True,
     )
     size: Mapped[str | None] = mapped_column(
         String(10),
         nullable=True,
     )
    
     # JSON field for any additional fields not predefined
     additional_data: Mapped[dict | None] = mapped_column(
         JSON,
         nullable=True,
     )
    
     # Timestamp
     created_at: Mapped[datetime] = mapped_column(
         DateTime,
         nullable=False,
         default=lambda: datetime.now(timezone.utc),
     )
    
     # Relationships
     planification: Mapped["Planification"] = relationship(
         "Planification",
         back_populates="records",
     )
     document: Mapped["Document"] = relationship(
         "Document",
         back_populates="record",
         uselist=False,  # One-to-one relationship
         cascade="all, delete-orphan",
     )
    
     def __repr__(self) -> str:
         return f"<Record: Container {self.container_number}>"

class Document(db.Model):
    """
    Fillable tarja document for Workers.
    
    Documents are automatically created from Records and Forms.
    Workers fill them during faenas by answering questions and taking photos.
    Once completed, the system generates a PDF tarja.
    
    This model supports offline functionality - workers can fill documents
    without connectivity and sync later.
    
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
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # Foreign keys
    record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("record.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one relationship
        index=True,
    )
    worker_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),  # Keep document if worker is deleted
        nullable=True,
        index=True,
    )
    
    # Document status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        # Valid statuses: pending, in_progress, completed, reviewed, approved
    )
    
    # Document content
    # responses format: {"question_id": "answer", ...}
    responses: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # photos format: [{"question_id": "q1", "path": "/path/to/photo.jpg", "timestamp": "..."}, ...]
    photos: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Generated PDF
    pdf_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Workflow timestamps
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
    
    # Offline sync support
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    is_synced: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,  # True by default, False when created/modified offline
    )
    
    # Standard timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    
    # Relationships
    record: Mapped["Record"] = relationship(
        "Record",
        back_populates="document",
    )
    worker: Mapped["User"] = relationship(
        "User",
        foreign_keys=[worker_id],
    )
    
    def start_filling(self, worker_id: str) -> None:
        """
        Mark document as started by a worker.
        
        Args:
            worker_id: ID of the worker starting to fill the document
        """
        self.worker_id = worker_id
        self.status = "in_progress"
        self.started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def complete_filling(self) -> None:
        """
        Mark document as completed by the worker.
        """
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_reviewed(self) -> None:
        """
        Mark document as reviewed by a planner.
        """
        self.status = "reviewed"
        self.reviewed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_synced(self) -> None:
        """
        Mark document as synced after offline changes.
        """
        self.is_synced = True
        self.synced_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"<Document: {self.id} ({self.status})>"