# docs_models.py
"""
Task and form management models for the Pytarjas application.

This module defines models for managing forms, plannings, records, and tasks 
used in the consolidation/deconsolidation tarja process.

The workflow is:
1. Planner creates a Planning and associates it with a Form
2. System creates Records (one per row/entry in the planning)
3. System auto-generates Tasks (based on the Form)
4. Workers fill Tasks during faenas
5. System generates PDF tarjas from completed Tasks 
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
        created_by_id: Foreign key to User who created this form template
        created_at: When the form was created
        updated_at: Last modification timestamp
        questions: Related Question objects (one-to-many)
        plannings: Plannings using this form (one-to-many)
        created_by: User who created this form template (many-to-one)
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

    created_by_id: Mapped[str | None]=mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    plannings: Mapped[list["Planning"]]=relationship(
        "Planning",
        back_populates="form"
    )
    created_by: Mapped["User"]=relationship(
        "User",
        foreign_keys=[created_by_id],
    )

class Question(db.Model):
    """
    Individual question/field within a Form.
    
    Attributes:
        id: Unique identifier (UUID)
        form_id: Foreign key to parent Form
        question_text: The question to display to the worker
        question_description: Detailed helper text shown below the question (NEW)
        question_type: Type of input (text, number, datetime, photo, select, file)
        is_required: Whether this question must be answered
        order: Display order within the form (lower numbers first)
        options: JSON field for select options, validation rules, etc.
                 For select type: {"choices": ["Option 1", "Option 2", ...]}
        created_at: When the question was created
        updated_at: Last modification timestamp
        form: Related Form object (many-to-one)
    
    Supported question_type values:
        - text: Single or multi-line text input
        - number: Numeric input (integer or decimal)
        - datetime: Date and/or time picker
        - photo: Camera/photo capture
        - select: Single selection from predefined options
        - file: File upload attachment
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
    
    # NEW FIELD: Description for the question
    question_description: Mapped[str | None]=mapped_column(
        Text,
        nullable=True,
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

class Planning(db.Model):
    """
    Work planning task created by Planner.
    
    SIMPLIFIED: Now directly contains Tasks without the Record middle layer.
    
    Attributes:
        id: Unique identifier (UUID)
        planner_id: Foreign key to User (Planner who created it)
        form_id: Foreign key to Form (template to use for tasks)
        file_path: Location of uploaded file - empty if created via UI
        file_name: Original filename - empty if created via UI
        status: Processing status (uploaded, processing, completed, error)
        client_name: Client who requested this work
        total_tasks: Number of tasks in this planning (was total_records)
        created_at: When the planning was created
        updated_at: Last modification timestamp
        planner: Related User (Planner) object (many-to-one)
        form: Related Form object (many-to-one)
        tasks: Related Task objects (one-to-many) - CHANGED from records
    """

    __tablename__="planning"

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
    
    # RENAMED: total_records → total_tasks (more accurate now)
    total_tasks: Mapped[int]=mapped_column(
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
        back_populates="plannings",
    )
    # CHANGED: records → tasks (direct relationship now)
    tasks: Mapped[list["Task"]]=relationship(
        "Task",
        back_populates="planning",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Planning: {self.client_name} - {self.total_tasks} tasks>"


# RECORD CLASS REMOVED - Its functionality has been merged into Task below


class Task(db.Model):
    """
    Fillable tarja task for Workers.
    
    SIMPLIFIED: Now contains task data directly (record_data) and references Planning.
    The Record middle layer has been removed for simplicity.
    
    Tasks can be created in two ways:
    1. Batch creation from Planning (planning_id is set)
    2. Manual creation (planning_id can be NULL)
    
    Attributes:
        id: Unique identifier (UUID)
        planning_id: Foreign key to Planning (NULL for manual tasks)
        form_id: Foreign key to Form (which template to use)
        record_data: JSON containing all task-specific data (merged from Record)
        worker_id: Foreign key to User (Worker who fills it)
        created_by_id: Foreign key to User (who created this task - for standalone tasks)
        status: Task status (pending, in_progress, completed, reviewed, approved)
        responses: JSON storing all question answers
        
        <PHOTOS AND PDF_PATH FIELDS REMOVED>
        
        started_at: When worker started filling the task
        completed_at: When worker finished filling the task
        reviewed_at: When planner reviewed the task
        synced_at: When offline data was synced to server
        is_synced: Whether offline changes are synced
        created_at: When the task was created
        updated_at: Last modification timestamp
        planning: Related Planning object (many-to-one) - CHANGED from record
        form: Related Form object (many-to-one) - NEW direct relationship
        worker: Related User (Worker) object (many-to-one)
        created_by: Related User object who created this task (many-to-one)
    
    Example record_data for different forms:
        Container form: {"container_number": "ABCD123", "ship_name": "MSC Luna", ...}
        Pallet form: {"pallet_number": "PLT-001", "warehouse": "A-15", ...}
        Booking form: {"booking_number": "BK2025001", "client": "ACME", ...}
    """
    __tablename__ = "task"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # CHANGED: record_id → planning_id (direct reference now)
    # NULLABLE: Allows manual task creation without planning
    planning_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("planning.id", ondelete="CASCADE"),
        nullable=True,  # NULL = manual task, not from planning
        index=True,
    )
    
    # NEW: Direct reference to Form (was accessed via record.planning.form)
    form_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    # NEW: Merged from Record - stores all task-specific data
    # Uses JSON for flexibility - different forms can have different fields
    record_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    
    worker_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # NEW: Track who created the task (for standalone tasks)
    created_by_id: Mapped[str | None] = mapped_column(
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
    
    # REMOVED: photos: Mapped[list | None] = mapped_column(JSON, nullable=True,)
    
    # REMOVED: pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True,)
    
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
    
    # CHANGED: record → planning (direct relationship now)
    planning: Mapped["Planning"] = relationship(
        "Planning",
        back_populates="tasks",
    )
    
    # NEW: Direct relationship to Form
    form: Mapped["Form"] = relationship(
        "Form",
        foreign_keys=[form_id],
    )
    
    worker: Mapped["User"] = relationship(
        "User",
        foreign_keys=[worker_id],
    )
    
    # NEW: User who created this task (for standalone tasks)
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    
    # ========================================================================
    # HELPER METHODS - Merged from Record class
    # ========================================================================
    
    def get_field(self, field_name: str, default=None):
        """
        Get a field from record_data with optional default value.
        """
        return self.record_data.get(field_name, default)
    
    def set_field(self, field_name: str, value):
        """
        Set a field in record_data and mark as modified.
        """
        self.record_data[field_name] = value
        flag_modified(self, 'record_data')
        self.updated_at = datetime.now(timezone.utc)
    
    def update_fields(self, fields_dict: dict):
        """
        Update multiple fields in record_data at once.
        """
        self.record_data.update(fields_dict)
        flag_modified(self, 'record_data')
        self.updated_at = datetime.now(timezone.utc)
    
    # ========================================================================
    # EXISTING METHODS - Unchanged
    # ========================================================================
    
    def start_filling(self, worker_id: str) -> None:
        """Mark task as started by a worker."""
        self.worker_id = worker_id
        self.status = "in_progress"
        self.started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def complete_filling(self) -> None:
        """Mark task as completed by the worker."""
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_reviewed(self) -> None:
        """Mark task as reviewed by a planner."""
        self.status = "reviewed"
        self.reviewed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_synced(self) -> None:
        """Mark task as synced after offline changes."""
        self.is_synced = True
        self.synced_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"<Task: {self.id} ({self.status})>"