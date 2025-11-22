"""
GraphQL Resolvers – v0.1 Implementation
This file implements the read-only resolvers defined in the design document.
"""

from typing import List, Optional

from alphatrion.metadata.sql import SQLStore
from alphatrion.metadata.sql_models import (
    Project as ProjectModel,
    Experiment as ExperimentModel,
    Trial as TrialModel,
    Run as RunModel,
    Metric as MetricModel,
)

from .types import Project, Experiment, Trial, Run, Metric


store = SQLStore(
    "postgresql+psycopg2://alphatrion:alphatr1on@localhost:5432/alphatrion"
)

# ---------------------------------------
# Helpers: SQLAlchemy model --> GraphQL type
# ---------------------------------------


def to_gql_project(p: ProjectModel) -> Project:
    """Convert SQLAlchemy Project → GraphQL Project."""
    return Project(
        id=str(p.uuid),
        name=p.name,
        description=p.description,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def to_gql_experiment(e: ExperimentModel) -> Experiment:
    """Convert SQLAlchemy Experiment → GraphQL Experiment."""
    return Experiment(
        id=str(e.uuid),
        project_id=str(e.project_id),
        name=e.name,
        description=e.description,
        meta=e.meta,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


def to_gql_trial(t: TrialModel) -> Trial:
    """Convert SQLAlchemy Trial → GraphQL Trial."""
    return Trial(
        id=str(t.uuid),
        experiment_id=str(t.experiment_id),
        meta=t.meta,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def to_gql_run(r: RunModel) -> Run:
    """Convert SQLAlchemy Run → GraphQL Run."""
    return Run(
        id=str(r.uuid),
        trial_id=str(r.trial_id),
        meta=r.meta,
        created_at=r.created_at,
    )


def to_gql_metric(m: MetricModel) -> Metric:
    """Convert SQLAlchemy Metric → GraphQL Metric."""
    return Metric(
        id=str(m.uuid),
        trial_id=str(m.trial_id),
        name=m.key,
        value=m.value,
        created_at=m.created_at,
    )


# ---------------------------------------
# Resolvers
# ---------------------------------------

class GraphQLResolvers:

    # -------------------------
    # Project
    # -------------------------

    @staticmethod
    def list_projects() -> List[Project]:
        """Return all projects."""
        rows = store.list_projects()
        return [to_gql_project(p) for p in rows]

    @staticmethod
    def get_project(id: str) -> Optional[Project]:
        """Return a single project by ID."""
        p = store.get_project(id)
        return to_gql_project(p) if p else None

    # -------------------------
    # Experiment
    # -------------------------

    @staticmethod
    def list_experiments(project_id: str) -> List[Experiment]:
        """
        Return all experiments belonging to a project.
        This satisfies the v0.1 'experiments(project_id)' query.
        """
        rows = store.list_exps(project_id, page=0, page_size=100)
        return [to_gql_experiment(e) for e in rows]

    @staticmethod
    def get_experiment(id: str) -> Optional[Experiment]:
        """Return a single experiment by ID."""
        e = store.get_exp(id)
        return to_gql_experiment(e) if e else None

    # -------------------------
    # Trial
    # -------------------------

    @staticmethod
    def list_trials(experiment_id: str) -> List[Trial]:
        """Return all trials for a given experiment."""
        session = store._session()
        rows = (
            session.query(TrialModel)
            .filter(TrialModel.experiment_id == experiment_id)
            .all()
        )
        session.close()
        return [to_gql_trial(t) for t in rows]

    @staticmethod
    def get_trial(id: str) -> Optional[Trial]:
        """Return a single trial by ID."""
        session = store._session()
        row = session.query(TrialModel).filter(TrialModel.uuid == id).first()
        session.close()
        return to_gql_trial(row) if row else None

    # -------------------------
    # Run
    # -------------------------

    @staticmethod
    def list_runs(trial_id: str) -> List[Run]:
        """Return all runs under a trial."""
        session = store._session()
        rows = (
            session.query(RunModel)
            .filter(RunModel.trial_id == trial_id)
            .all()
        )
        session.close()
        return [to_gql_run(r) for r in rows]

    @staticmethod
    def get_run(id: str) -> Optional[Run]:
        """Return a single run by ID."""
        session = store._session()
        row = session.query(RunModel).filter(RunModel.uuid == id).first()
        session.close()
        return to_gql_run(row) if row else None

    # -------------------------
    # Metric
    # -------------------------

    @staticmethod
    def list_trial_metrics(trial_id: str) -> List[Metric]:
        """Return all metrics for a trial."""
        session = store._session()
        rows = (
            session.query(MetricModel)
            .filter(MetricModel.trial_id == trial_id)
            .all()
        )
        session.close()
        return [to_gql_metric(m) for m in rows]
