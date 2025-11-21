from typing import List, Optional

from alphatrion.metadata.sql import SQLStore
from alphatrion.metadata.sql_models import (
    Project as ProjectModel,
    Experiment as ExperimentModel,
)

from .types import Project, Experiment


store = SQLStore(
    "postgresql+psycopg2://alphatrion:alphatr1on@localhost:5432/alphatrion")


# ---------------------------
# Helpers: SQLAlchemy → GraphQL
# ---------------------------

def to_gql_project(p: ProjectModel) -> Project:
    return Project(
        id=str(p.uuid),
        name=p.name,
        description=p.description,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def to_gql_experiment(e: ExperimentModel) -> Experiment:
    return Experiment(
        id=str(e.uuid),
        project_id=str(e.project_id),
        name=e.name,
        description=e.description,
        meta=e.meta,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


# ---------------------------
# GraphQL Resolvers
# ---------------------------

class GraphQLResolvers:

    # --- Project ---

    @staticmethod
    def list_projects() -> List[Project]:
        rows = store.list_projects()
        return [to_gql_project(p) for p in rows]

    @staticmethod
    def get_project(id: str) -> Optional[Project]:
        p = store.get_project(id)
        return to_gql_project(p) if p else None

    # --- Experiment ---

    @staticmethod
    def list_experiments(project_id: str) -> List[Experiment]:
        rows = store.list_exps(project_id, page=0, page_size=100)
        return [to_gql_experiment(e) for e in rows]

    @staticmethod
    def get_experiment(id: str) -> Optional[Experiment]:
        e = store.get_exp(id)
        return to_gql_experiment(e) if e else None

    # --- Leave Trials/Runs/Metrics empty for now ---

    @staticmethod
    def list_trials(experiment_id: str) -> list:
        return []

    @staticmethod
    def get_trial(id: str):
        return None

    @staticmethod
    def list_runs(trial_id: str) -> list:
        return []

    @staticmethod
    def get_run(id: str):
        return None

    @staticmethod
    def list_trial_metrics(trial_id: str) -> list:
        return []
