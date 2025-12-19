# docs_models.py
"""
Task and form management models for the Pytarjas application.
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
    Now supports VERSIONING to preserve historical data.
    """
    __tablename__="form"

    id: Mapped[str]=mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # CHANGED: Removed unique=True to allow multiple versions with same name
    name: Mapped[str]=mapped_column(
        String(100),
        nullable=False,
        unique=False, 
        index=True,
    )
    
    # NEW: Version number (starts at 1)
    version: Mapped[int]=mapped_column(
        Integer,
        nullable=False,
        default=1,
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
    
    # NEW: Helper to get display name with version
    @property
    def display_name(self):
        if self.version > 1:
            return f"{self.name} (v{self.version})"
        return self.name

class Question(db.Model):
    """
    Individual question/field within a Form.
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
    # ... (Rest of Planning model remains identical to your file) ...
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
    tasks: Mapped[list["Task"]]=relationship(
        "Task",
        back_populates="planning",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Planning: {self.client_name} - {self.total_tasks} tasks>"

class Task(db.Model):
    # ... (Rest of Task model remains identical to your file) ...
    __tablename__ = "task"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    planning_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("planning.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    form_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
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
    
    planning: Mapped["Planning"] = relationship(
        "Planning",
        back_populates="tasks",
    )
    
    form: Mapped["Form"] = relationship(
        "Form",
        foreign_keys=[form_id],
    )
    
    worker: Mapped["User"] = relationship(
        "User",
        foreign_keys=[worker_id],
    )
    
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    
    def get_field(self, field_name: str, default=None):
        return self.record_data.get(field_name, default)
    
    def set_field(self, field_name: str, value):
        self.record_data[field_name] = value
        flag_modified(self, 'record_data')
        self.updated_at = datetime.now(timezone.utc)
    
    def update_fields(self, fields_dict: dict):
        self.record_data.update(fields_dict)
        flag_modified(self, 'record_data')
        self.updated_at = datetime.now(timezone.utc)
    
    def start_filling(self, worker_id: str) -> None:
        self.worker_id = worker_id
        self.status = "in_progress"
        self.started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def complete_filling(self) -> None:
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_reviewed(self) -> None:
        self.status = "reviewed"
        self.reviewed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_synced(self) -> None:
        self.is_synced = True
        self.synced_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"<Task: {self.id} ({self.status})>"