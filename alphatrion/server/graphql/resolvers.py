import uuid

from alphatrion.metadata.sql_models import Status
from alphatrion.server.graphql import runtime

from .types import (
    Experiment,
    GraphQLExperimentType,
    GraphQLExperimentTypeEnum,
    GraphQLStatusEnum,
    Metric,
    Project,
    Run,
    Trial,
)


class GraphQLResolvers:
    @staticmethod
    def list_projects(page: int = 0, page_size: int = 10) -> list[Project]:
        metadb = runtime.graphql_runtime().metadb
        projects = metadb.list_projects(page=page, page_size=page_size)
        return [
            Project(
                id=p.uuid,
                name=p.name,
                description=p.description,
                meta=p.meta,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in projects
        ]

    @staticmethod
    def get_project(id: str) -> Project | None:
        metadb = runtime.graphql_runtime().metadb
        project = metadb.get_project(project_id=uuid.UUID(id))
        if project:
            return Project(
                id=project.uuid,
                name=project.name,
                description=project.description,
                meta=project.meta,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
        return None

    @staticmethod
    def list_experiments(
        project_id: str, page: int = 0, page_size: int = 10
    ) -> list[Experiment]:
        metadb = runtime.graphql_runtime().metadb
        exps = metadb.list_exps(
            project_id=uuid.UUID(project_id), page=page, page_size=page_size
        )
        return [
            Experiment(
                id=exp.uuid,
                project_id=exp.project_id,
                name=exp.name,
                description=exp.description,
                meta=exp.meta,
                kind=GraphQLExperimentTypeEnum[GraphQLExperimentType(exp.kind).name],
                created_at=exp.created_at,
                updated_at=exp.updated_at,
            )
            for exp in exps
        ]

    @staticmethod
    def get_experiment(id: str) -> Experiment | None:
        metadb = runtime.graphql_runtime().metadb
        exp = metadb.get_exp(exp_id=uuid.UUID(id))
        if exp:
            return Experiment(
                id=exp.uuid,
                project_id=exp.project_id,
                name=exp.name,
                description=exp.description,
                meta=exp.meta,
                kind=GraphQLExperimentTypeEnum[GraphQLExperimentType(exp.kind).name],
                created_at=exp.created_at,
                updated_at=exp.updated_at,
            )
        return None

    @staticmethod
    def list_trials(
        experiment_id: str, page: int = 0, page_size: int = 10
    ) -> list[Trial]:
        metadb = runtime.graphql_runtime().metadb
        trials = metadb.list_trials_by_experiment_id(
            experiment_id=uuid.UUID(experiment_id), page=page, page_size=page_size
        )
        return [
            Trial(
                id=t.uuid,
                experiment_id=t.experiment_id,
                project_id=t.project_id,
                name=t.name,
                description=t.description,
                meta=t.meta,
                params=t.params,
                duration=t.duration,
                status=GraphQLStatusEnum[Status(t.status).name],
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in trials
        ]

    @staticmethod
    def get_trial(id: str) -> Trial | None:
        metadb = runtime.graphql_runtime().metadb
        trial = metadb.get_trial(trial_id=uuid.UUID(id))
        if trial:
            return Trial(
                id=trial.uuid,
                experiment_id=trial.experiment_id,
                project_id=trial.project_id,
                name=trial.name,
                description=trial.description,
                meta=trial.meta,
                params=trial.params,
                duration=trial.duration,
                status=GraphQLStatusEnum[Status(trial.status).name],
                created_at=trial.created_at,
                updated_at=trial.updated_at,
            )
        return None

    @staticmethod
    def list_runs(trial_id: str, page: int = 0, page_size: int = 10) -> list[Run]:
        metadb = runtime.graphql_runtime().metadb
        runs = metadb.list_runs_by_trial_id(
            trial_id=uuid.UUID(trial_id), page=page, page_size=page_size
        )
        return [
            Run(
                id=r.uuid,
                trial_id=r.trial_id,
                project_id=r.project_id,
                experiment_id=r.experiment_id,
                meta=r.meta,
                status=GraphQLStatusEnum[Status(r.status).name],
                created_at=r.created_at,
            )
            for r in runs
        ]

    @staticmethod
    def get_run(id: str) -> Run | None:
        metadb = runtime.graphql_runtime().metadb
        run = metadb.get_run(run_id=uuid.UUID(id))
        if run:
            return Run(
                id=run.uuid,
                trial_id=run.trial_id,
                project_id=run.project_id,
                experiment_id=run.experiment_id,
                meta=run.meta,
                status=GraphQLStatusEnum[Status(run.status).name],
                created_at=run.created_at,
            )
        return None

    @staticmethod
    def list_trial_metrics(
        trial_id: str, page: int = 0, page_size: int = 10
    ) -> list[Metric]:
        metadb = runtime.graphql_runtime().metadb
        metrics = metadb.list_metrics_by_trial_id(
            trial_id=uuid.UUID(trial_id), page=page, page_size=page_size
        )
        return [
            Metric(
                id=m.uuid,
                key=m.key,
                value=m.value,
                project_id=m.project_id,
                experiment_id=m.experiment_id,
                trial_id=m.trial_id,
                run_id=m.run_id,
                step=m.step,
                created_at=m.created_at,
            )
            for m in metrics
        ]
