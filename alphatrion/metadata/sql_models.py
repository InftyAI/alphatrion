import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Enum, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TrialStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


COMPLETED_STATUS = [TrialStatus.FINISHED, TrialStatus.FAILED]


class Project(Base):
    __tablename__ = "projects"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC)
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


# Define the Experiment model for SQLAlchemy
class Experiment(Base):
    __tablename__ = "experiments"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    meta = Column(JSON, nullable=True, comment="Additional metadata for the experiment")

    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC)
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
    status = Column(
        Enum(TrialStatus),
        default=TrialStatus.PENDING,
        nullable=False,
        comment="Status of the trial",
    )

    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC)
    )


class Run(Base):
    __tablename__ = "runs"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    trial_id = Column(UUID(as_uuid=True), nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC)
    )


class Model(Base):
    __tablename__ = "models"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    version = Column(String, nullable=False)
    meta = Column(JSON, nullable=True, comment="Additional metadata for the model")

    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC)
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


class Metric(Base):
    __tablename__ = "metrics"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    trial_id = Column(UUID(as_uuid=True), nullable=False)
    run_id = Column(UUID(as_uuid=True), nullable=False)
    step = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
