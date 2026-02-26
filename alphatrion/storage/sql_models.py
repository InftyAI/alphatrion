import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
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


class Team(Base):
    __tablename__ = "teams"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    meta = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Additional metadata for the team",
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


class User(Base):
    __tablename__ = "users"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    avatar_url = Column(String, nullable=True)
    meta = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Additional metadata for the user",
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


class TeamMember(Base):
    __tablename__ = "team_members"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (UniqueConstraint("team_id", "user_id", name="unique_team_user"),)


# Define the Project model for SQLAlchemy
class Project(Base):
    __tablename__ = "projects"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    creator_id = Column(UUID(as_uuid=True), nullable=True)
    meta = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Additional metadata for the project",
    )

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


class Experiment(Base):
    __tablename__ = "experiments"
    __table_args__ = (Index("ix_experiments_project_id", "project_id"),)

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    meta = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Additional metadata for the experiment",
    )
    params = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Parameters for the experiment",
    )
    kind = Column(
        Integer,
        default=ExperimentType.CRAFT_EXPERIMENT,
        nullable=False,
        comment="Type of the experiment",
    )
    duration = Column(Float, default=0.0, comment="Duration of the experiment in seconds")
    status = Column(
        Integer,
        default=Status.PENDING,
        nullable=False,
        comment="Status of the experiment, \
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
    __table_args__ = (Index("ix_runs_experiment_id", "experiment_id"),)

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    meta = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Additional metadata for the run",
    )
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
    team_id = Column(UUID(as_uuid=True), nullable=False)
    version = Column(String, nullable=False)
    meta = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Additional metadata for the model",
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (
        Index("ix_metrics_experiment_id_key", "experiment_id", "key"),
    )

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), nullable=False)
    run_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))


class ContentSnapshot(Base):
    __tablename__ = "content_snapshots"
    __table_args__ = (
        Index("ix_content_snapshots_experiment_id", "experiment_id"),
        Index("ix_content_snapshots_experiment_id_is_del", "experiment_id", "is_del"),
    )

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), nullable=False)
    run_id = Column(
        UUID(as_uuid=True), nullable=True, comment="Run ID, null for seed content"
    )

    content_uid = Column(
        String, nullable=False, comment="UID for content identification"
    )
    content_text = Column(String, nullable=False, comment="Actual code content as text")

    parent_uid = Column(
        String, nullable=True, comment="Parent content UID (null for seed)"
    )
    co_parent_uids = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="List of co-parent UIDs for crossover",
    )

    fitness = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Multi-dimensional fitness values",
    )
    evaluation = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Full evaluation results",
    )
    metainfo = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Additional metadata for the content snapshot",
    )

    language = Column(
        String,
        nullable=True,
        default="python",
        comment="Programming language for syntax highlighting",
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")
