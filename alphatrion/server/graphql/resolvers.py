import uuid

from alphatrion.server.graphql import runtime
from alphatrion.storage.sql_models import Status

from .types import (
    Experiment,
    GraphQLExperimentType,
    GraphQLExperimentTypeEnum,
    GraphQLStatusEnum,
    Metric,
    Project,
    Run,
    Team,
    User,
)


class GraphQLResolvers:
    @staticmethod
    def list_teams(page: int = 0, page_size: int = 10) -> list[Team]:
        metadb = runtime.graphql_runtime().metadb
        teams = metadb.list_teams(page=page, page_size=page_size)
        return [
            Team(
                id=t.uuid,
                name=t.name,
                description=t.description,
                meta=t.meta,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in teams
        ]

    @staticmethod
    def get_team(id: str) -> Team | None:
        metadb = runtime.graphql_runtime().metadb
        team = metadb.get_team(team_id=uuid.UUID(id))
        if team:
            return Team(
                id=team.uuid,
                name=team.name,
                description=team.description,
                meta=team.meta,
                created_at=team.created_at,
                updated_at=team.updated_at,
            )
        return None

    @staticmethod
    def get_user(id: str) -> User | None:
        metadb = runtime.graphql_runtime().metadb
        user = metadb.get_user(user_id=uuid.UUID(id))
        if user:
            return User(
                id=user.uuid,
                username=user.username,
                email=user.email,
                team_id=user.team_id,
                meta=user.meta,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        return None

    @staticmethod
    def list_projects(
        team_id: str, page: int = 0, page_size: int = 10
    ) -> list[Project]:
        metadb = runtime.graphql_runtime().metadb
        projects = metadb.list_projects(
            team_id=uuid.UUID(team_id), page=page, page_size=page_size
        )
        return [
            Project(
                id=proj.uuid,
                team_id=proj.team_id,
                creator_id=proj.creator_id,
                name=proj.name,
                description=proj.description,
                meta=proj.meta,
                created_at=proj.created_at,
                updated_at=proj.updated_at,
            )
            for proj in projects
        ]

    @staticmethod
    def get_project(id: str) -> Project | None:
        metadb = runtime.graphql_runtime().metadb
        proj = metadb.get_project(project_id=uuid.UUID(id))
        if proj:
            return Project(
                id=proj.uuid,
                team_id=proj.team_id,
                creator_id=proj.creator_id,
                name=proj.name,
                description=proj.description,
                meta=proj.meta,
                created_at=proj.created_at,
                updated_at=proj.updated_at,
            )
        return None

    @staticmethod
    def list_experiments(
        project_id: str, page: int = 0, page_size: int = 10
    ) -> list[Experiment]:
        metadb = runtime.graphql_runtime().metadb
        exps = metadb.list_exps_by_project_id(
            project_id=uuid.UUID(project_id), page=page, page_size=page_size
        )
        return [
            Experiment(
                id=e.uuid,
                team_id=e.team_id,
                user_id=e.user_id,
                project_id=e.project_id,
                name=e.name,
                description=e.description,
                meta=e.meta,
                params=e.params,
                duration=e.duration,
                status=GraphQLStatusEnum[Status(e.status).name],
                kind=GraphQLExperimentTypeEnum[GraphQLExperimentType(e.kind).name],
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in exps
        ]

    @staticmethod
    def get_experiment(id: str) -> Experiment | None:
        metadb = runtime.graphql_runtime().metadb
        exp = metadb.get_experiment(experiment_id=uuid.UUID(id))
        if exp:
            return Experiment(
                id=exp.uuid,
                team_id=exp.team_id,
                user_id=exp.user_id,
                project_id=exp.project_id,
                name=exp.name,
                description=exp.description,
                meta=exp.meta,
                params=exp.params,
                duration=exp.duration,
                status=GraphQLStatusEnum[Status(exp.status).name],
                kind=GraphQLExperimentTypeEnum[GraphQLExperimentType(exp.kind).name],
                created_at=exp.created_at,
                updated_at=exp.updated_at,
            )
        return None

    @staticmethod
    def list_runs(experiment_id: str, page: int = 0, page_size: int = 10) -> list[Run]:
        metadb = runtime.graphql_runtime().metadb
        runs = metadb.list_runs_by_exp_id(
            exp_id=uuid.UUID(experiment_id), page=page, page_size=page_size
        )
        return [
            Run(
                id=r.uuid,
                team_id=r.team_id,
                user_id=r.user_id,
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
                team_id=run.team_id,
                user_id=run.user_id,
                project_id=run.project_id,
                experiment_id=run.experiment_id,
                meta=run.meta,
                status=GraphQLStatusEnum[Status(run.status).name],
                created_at=run.created_at,
            )
        return None

    @staticmethod
    def list_exp_metrics(
        experiment_id: str, page: int = 0, page_size: int = 10
    ) -> list[Metric]:
        metadb = runtime.graphql_runtime().metadb
        metrics = metadb.list_metrics_by_experiment_id(
            experiment_id=uuid.UUID(experiment_id), page=page, page_size=page_size
        )
        return [
            Metric(
                id=m.uuid,
                key=m.key,
                value=m.value,
                team_id=m.team_id,
                project_id=m.project_id,
                experiment_id=m.experiment_id,
                run_id=m.run_id,
                created_at=m.created_at,
            )
            for m in metrics
        ]
