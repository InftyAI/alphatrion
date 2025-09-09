import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ExperimentStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


COMPLETED_STATUS = [ExperimentStatus.FINISHED, ExperimentStatus.FAILED]


# Define the Experiment model for SQLAlchemy
class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    project_id = Column(String, nullable=False)
    status = Column(
        Enum(ExperimentStatus), nullable=False, default=ExperimentStatus.PENDING
    )
    meta = Column(JSON, nullable=True, comment="Additional metadata for the experiment")
    labels = Column(JSON, nullable=True, comment="Labels for the experiment")
    duration = Column(Integer, default=0, comment="Duration in seconds")

    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC)
    )
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")
