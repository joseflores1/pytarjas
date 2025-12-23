# docs_models.py
"""
Task and form management models for the Pytarjas application.
Includes Planning Templates for dynamic batch metadata and Task-level metadata.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .user_models import db, User

class PlanningTemplate(db.Model):
    """
    Template for Planning metadata (the 'header' information for a batch of tasks).
    """
    __tablename__ = "planning_template"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    fields: Mapped[list["PlanningMetadataField"]] = relationship(
        "PlanningMetadataField",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="PlanningMetadataField.order",
    )
    
    plannings: Mapped[list["Planning"]] = relationship(
        "Planning",
        back_populates="template"
    )

    def __repr__(self):
        return f"<PlanningTemplate: {self.name}>"

class PlanningMetadataField(db.Model):
    """
    Individual metadata field definition within a PlanningTemplate.
    """
    __tablename__ = "planning_metadata_field"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    template_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("planning_template.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    field_label: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    field_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="text",
    )

    is_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    options: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    template: Mapped["PlanningTemplate"] = relationship(
        "PlanningTemplate",
        back_populates="fields",
    )

class Form(db.Model):
    """
    Predefined questionnaire template for tasks.
    Supports versioning to preserve historical data.
    """
    __tablename__ = "form"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    form_type: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_by_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="form",
        cascade="all, delete-orphan",
    )

    plannings: Mapped[list["Planning"]] = relationship(
        "Planning",
        back_populates="form"
    )

    @property
    def display_name(self):
        if self.version > 1:
            return f"{self.name} (v{self.version})"
        
        return self.name

class Question(db.Model):
    """
    Individual question within a Form.
    """
    __tablename__ = "question"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    form_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    question_text: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    
    question_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    question_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    is_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    options: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )
        
    form: Mapped["Form"] = relationship(
        "Form",
        back_populates="questions",
    )

class Planning(db.Model):
    """
    Instance of a planning, grouping several tasks and holding batch metadata.
    """
    __tablename__ = "planning"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    planner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
 
    form_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    template_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("planning_template.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    metadata_values: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    file_path: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    file_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="uploaded",
        index=True,
    )

    client_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        index=True,
    )
    
    total_tasks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    planner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[planner_id],
    )

    form: Mapped["Form"] = relationship(
        "Form",
        back_populates="plannings",
    )
    
    template: Mapped["PlanningTemplate"] = relationship(
        "PlanningTemplate",
        back_populates="plannings",
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="planning",
        cascade="all, delete-orphan",
    )

class Task(db.Model):
    """
    Individual work record (tarja) associated with a planning or created singularly.
    """
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
    
    # Task-specific input metadata (equivalent to Planning metadata for singular tasks)
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
    
    # Worker's answers to the Form questions
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
        onupdate=lambda: datetime.now(timezone.utc),
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