import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
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
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        # Prevents duplicate team memberships and creates index on (team_id, user_id)
        # This index covers queries filtering by team_id (via leftmost prefix rule)
        UniqueConstraint("team_id", "user_id", name="unique_team_user"),
    )


class ExperimentType(enum.IntEnum):
    UNKNOWN = 0
    CRAFT_EXPERIMENT = 1


class Experiment(Base):
    __tablename__ = "experiments"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False)
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
    duration = Column(
        Float, default=0.0, comment="Duration of the experiment in seconds"
    )
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

    __table_args__ = (
        # For get_exp_by_name() - line 407-412: (team_id, name, is_del)
        Index("idx_experiment_team_name", "team_id", "name", "is_del"),
        # For list_exps_by_team_id() - line 428-429: (team_id, is_del) +
        # ORDER BY created_at
        # For list_exps_by_timeframe() - line 521-528: (team_id, created_at range,
        # is_del)
        # For count_experiments() - line 507-515: (team_id, is_del)
        Index("idx_experiment_team_active_time", "team_id", "is_del", "created_at"),
    )


class Run(Base):
    __tablename__ = "runs"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    meta = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        comment="Additional metadata for the run",
    )
    duration = Column(Float, default=0.0, comment="Duration of the run in seconds")
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

    __table_args__ = (
        # For list_runs_by_exp_id() - line 592: (experiment_id, is_del) +
        # ORDER BY created_at
        Index("idx_run_experiment_active", "experiment_id", "is_del", "created_at"),
        # For count_runs() - line 606: (team_id, is_del)
        Index("idx_run_team_active", "team_id", "is_del"),
    )


# class Model(Base):
#     __tablename__ = "models"

#     uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     name = Column(String, nullable=False, unique=True)
#     description = Column(String, nullable=True)
#     team_id = Column(UUID(as_uuid=True), nullable=False)
#     version = Column(String, nullable=False)
#     meta = Column(
#         MutableDict.as_mutable(JSON),
#         nullable=True,
#         comment="Additional metadata for the model",
#     )

#     created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
#     updated_at = Column(
#         DateTime(timezone=True),
#         default=lambda: datetime.now(UTC),
#         onupdate=lambda: datetime.now(UTC),
#     )
#     is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")


class Metric(Base):
    __tablename__ = "metrics"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), nullable=False)
    run_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))

    __table_args__ = (
        # For list_metrics_by_experiment_id() - line 639: filter + ORDER BY created_at
        Index("idx_metric_experiment_time", "experiment_id", "created_at"),
        # For list_metrics_by_run_id() - line 650: filter + ORDER BY created_at
        # Note: UniqueConstraint below provides (run_id, key) index, but not optimal
        # for ORDER BY created_at
        Index("idx_metric_run_time", "run_id", "created_at"),
        # Unique constraint for data integrity
        UniqueConstraint("run_id", "key", name="idx_unique_metric"),
    )


class ExperimentLabel(Base):
    __tablename__ = "experiment_labels"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), nullable=False)
    label_name = Column(String, nullable=False)
    label_value = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        # For list_labels_by_exp_id() - line 446: filter by experiment_id
        # For list_exps_by_label() join - line 464-474: join + filter by
        # label_name/value
        # This composite index covers both via leftmost prefix rule
        Index(
            "idx_experiment_label_lookup", "experiment_id", "label_name", "label_value"
        ),
    )
