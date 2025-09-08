from datetime import datetime, timezone
import enum

from sqlalchemy import Column, Integer, String, Enum, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ExperimentStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


# Define the Experiment model for SQLAlchemy
class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    project_id = Column(String, nullable=False)
    status = Column(Enum(ExperimentStatus), nullable=False, default=ExperimentStatus.PENDING)
    meta = Column(JSON, nullable=True, comment="Additional metadata for the experiment")

    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_del = Column(Integer, default=0, comment="0 for not deleted, 1 for deleted")
