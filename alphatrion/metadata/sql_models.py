import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Status(enum.IntEnum):
    UNKNOWN = 0
    PENDING = 1
    RUNNING = 2
    COMPLETED = 9
    CANCELLED = 10
    FAILED = 11


StatusMap = {
    Status.UNKNOWN: "UNKNOWN",
    Status.PENDING: "PENDING",
    Status.RUNNING: "RUNNING",
    Status.CANCELLED: "CANCELLED",
    Status.COMPLETED: "COMPLETED",
    Status.FAILED: "FAILED",
}

FINISHED_STATUS = [Status.COMPLETED, Status.FAILED, Status.CANCELLED]


class Project(Base):
    __tablename__ = "projects"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    meta = Column(JSON, nullable=True, comment="Additional metadata for the project")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


class ExperimentType(enum.IntEnum):
    UNKNOWN = 0
    CRAFT_EXPERIMENT = 1


# Define the Experiment model for SQLAlchemy
class Experiment(Base):
    __tablename__ = "experiments"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    meta = Column(JSON, nullable=True, comment="Additional metadata for the experiment")
    kind = Column(
        Integer,
        default=ExperimentType.CRAFT_EXPERIMENT,
        nullable=False,
        comment="Type of the experiment",
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


class Trial(Base):
    __tablename__ = "trials"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    meta = Column(JSON, nullable=True, comment="Additional metadata for the trial")
    params = Column(JSON, nullable=True, comment="Parameters for the experiment")
    duration = Column(Float, default=0.0, comment="Duration of the trial in seconds")
    status = Column(
        Integer,
        default=Status.PENDING,
        nullable=False,
        comment="Status of the trial, \
            0: UNKNOWN, 1: PENDING, 2: RUNNING, 9: COMPLETED, \
            10: CANCELLED, 11: FAILED",
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


class Run(Base):
    __tablename__ = "runs"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), nullable=False)
    trial_id = Column(UUID(as_uuid=True), nullable=False)
    meta = Column(JSON, nullable=True, comment="Additional metadata for the run")
    status = Column(
        Integer,
        default=Status.PENDING,
        nullable=False,
        comment="Status of the run, \
            0: UNKNOWN, 1: PENDING, 2: RUNNING, 9: COMPLETED, \
            10: CANCELLED, 11: FAILED",
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


class Model(Base):
    __tablename__ = "models"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    version = Column(String, nullable=False)
    meta = Column(JSON, nullable=True, comment="Additional metadata for the model")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


class Metric(Base):
    __tablename__ = "metrics"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), nullable=False)
    trial_id = Column(UUID(as_uuid=True), nullable=False)
    run_id = Column(UUID(as_uuid=True), nullable=False)
    step = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
