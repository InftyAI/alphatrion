import os
import uuid
from datetime import datetime

import httpx
import strawberry
from strawberry.types import Info

from alphatrion import envs
from alphatrion.artifact import artifact
from alphatrion.server.graphql.context import GraphQLContext
from alphatrion.server.graphql.types import ArtifactFile
from alphatrion.storage import runtime
from alphatrion.storage.sql_models import (
    AgentType,
    Status,
    StatusMap,
)

from .types import (
    AddUserToTeamInput,
    Agent,
    ArtifactContent,
    ArtifactRepository,
    ArtifactTag,
    CreateExperimentInput,
    CreateTeamInput,
    CreateUserInput,
    DailyCostUsage,
    Dataset,
    Experiment,
    GraphQLAgentTypeEnum,
    GraphQLExperimentType,
    GraphQLExperimentTypeEnum,
    GraphQLStatusEnum,
    Label,
    Metric,
    ModelDistribution,
    Organization,
    RemoveUserFromTeamInput,
    Run,
    Session,
    Span,
    Team,
    TraceEvent,
    TraceLink,
    UpdateExperimentInput,
    UpdateOrganizationInput,
    UpdateUserInput,
    User,
)


class GraphQLResolvers:
    @staticmethod
    def list_teams(
        info: Info[GraphQLContext, None], user_id: strawberry.ID | None = None
    ) -> list[Team]:
        if user_id is None:
            user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        teams = metadb.list_user_teams(user_id=user_id)
        return [
            Team(
                id=t.uuid,
                org_id=t.org_id,
                name=t.name,
                description=t.description,
                meta=t.meta,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in teams
        ]

    @staticmethod
    def get_team(info: Info[GraphQLContext, None], id: strawberry.ID) -> Team | None:
        user_id = info.context.user_id

        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        team = metadb.get_team(team_id=id)
        if team:
            return Team(
                id=team.uuid,
                org_id=team.org_id,
                name=team.name,
                description=team.description,
                meta=team.meta,
                created_at=team.created_at,
                updated_at=team.updated_at,
            )
        return None

    @staticmethod
    def get_user(info: Info[GraphQLContext, None], id: strawberry.ID) -> User | None:
        user_id = info.context.user_id
        org_id = info.context.org_id
        metadb = runtime.storage_runtime().metadb
        if (
            not metadb.user_is_super_admin_in_org(
                user_id=user_id, org_id=uuid.UUID(org_id)
            )
            and str(id) != user_id
        ):
            raise RuntimeError(
                "Not allowed to access user that is not yourself or you are not super admin in the org"
            )

        user = metadb.get_user(user_id=id)
        if user:
            return User(
                id=user.uuid,
                org_id=user.org_id,
                name=user.name,
                email=user.email,
                avatar_url=user.avatar_url,
                meta=user.meta,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        return None

    @staticmethod
    def get_organization(
        info: Info[GraphQLContext, None], id: strawberry.ID
    ) -> Organization | None:
        metadb = runtime.storage_runtime().metadb
        if not metadb.org_is_accessible_to_user(
            org_id=id, user_id=info.context.user_id
        ):
            raise RuntimeError(
                "Not allowed to access organization that user does not belong to"
            )

        org = metadb.get_organization(org_id=id)
        if org:
            return Organization(
                id=org.uuid,
                name=org.name,
                description=org.description,
                meta=org.meta,
                created_at=org.created_at,
                updated_at=org.updated_at,
            )
        return None

    @staticmethod
    def list_labels_by_exp_id(
        info: Info[GraphQLContext, None], experiment_id: strawberry.ID
    ) -> list[Label]:
        user_id = info.context.user_id

        metadb = runtime.storage_runtime().metadb
        if not metadb.experiment_is_accessible_to_user(
            experiment_id=experiment_id, user_id=user_id
        ):
            raise RuntimeError(
                "Not allowed to access experiment that user does not belong to"
            )

        # users belong to the same team can see all the experiments in the team.
        labels = metadb.list_labels_by_exp_id(experiment_id)
        return [
            Label(
                name=label.label_name,
                value=label.label_value,
            )
            for label in labels
        ]

    @staticmethod
    def list_tags_by_exp_id(
        info: Info[GraphQLContext, None], experiment_id: strawberry.ID
    ) -> list[str]:
        user_id = info.context.user_id

        metadb = runtime.storage_runtime().metadb
        if not metadb.experiment_is_accessible_to_user(
            experiment_id=experiment_id, user_id=user_id
        ):
            raise RuntimeError(
                "Not allowed to access experiment that user does not belong to"
            )

        tags = metadb.list_tags_by_exp_id(experiment_id)
        return [t.tag for t in tags]

    @staticmethod
    def list_experiments(
        info: Info[GraphQLContext, None],
        team_id: strawberry.ID,
        page: int = 0,
        page_size: int = 20,
        order_by: str = "created_at",
        order_desc: bool = True,
        label_name: str | None = None,
        label_value: str | None = None,
        tag: str | None = None,
    ) -> list[Experiment]:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        exps = metadb.list_experiments(
            team_id=team_id,
            label_name=label_name,
            label_value=label_value,
            tag=tag,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
        )

        return [
            Experiment(
                id=e.uuid,
                org_id=e.org_id,
                team_id=e.team_id,
                user_id=e.user_id,
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
    def get_experiment(
        info: Info[GraphQLContext, None], id: strawberry.ID
    ) -> Experiment | None:
        metadb = runtime.storage_runtime().metadb
        user_id = info.context.user_id
        if not metadb.experiment_is_accessible_to_user(
            experiment_id=id, user_id=user_id
        ):
            raise RuntimeError(
                "Not allowed to access experiment that user does not belong to"
            )

        exp = metadb.get_experiment(experiment_id=uuid.UUID(id))
        if exp:
            return Experiment(
                id=exp.uuid,
                org_id=exp.org_id,
                team_id=exp.team_id,
                user_id=exp.user_id,
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
    def list_runs(
        info: Info[GraphQLContext, None],
        experiment_id: strawberry.ID,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Run]:
        metadb = runtime.storage_runtime().metadb
        user_id = info.context.user_id
        if not metadb.experiment_is_accessible_to_user(
            experiment_id=experiment_id, user_id=user_id
        ):
            raise RuntimeError(
                "Not allowed to access experiment that user does not belong to"
            )

        runs = metadb.list_runs_by_exp_id(
            experiment_id=uuid.UUID(experiment_id),
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
        )
        return [
            Run(
                id=str(r.uuid),
                org_id=str(r.org_id),
                team_id=str(r.team_id),
                user_id=str(r.user_id),
                experiment_id=str(r.experiment_id) if r.experiment_id else None,
                session_id=str(r.session_id) if r.session_id else None,
                meta=r.meta,
                status=GraphQLStatusEnum[Status(r.status).name],
                duration=r.duration,
                created_at=r.created_at,
            )
            for r in runs
        ]

    @staticmethod
    def get_run(info: Info[GraphQLContext, None], id: strawberry.ID) -> Run | None:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.run_is_accessible_to_user(run_id=id, user_id=user_id):
            raise RuntimeError("Not allowed to access run that user does not belong to")

        run = metadb.get_run(run_id=uuid.UUID(id))
        if run:
            return Run(
                id=str(run.uuid),
                org_id=str(run.org_id),
                team_id=str(run.team_id),
                user_id=str(run.user_id),
                experiment_id=str(run.experiment_id) if run.experiment_id else None,
                session_id=str(run.session_id) if run.session_id else None,
                meta=run.meta,
                status=GraphQLStatusEnum[Status(run.status).name],
                duration=run.duration,
                created_at=run.created_at,
            )
        return None

    # Agent resolvers
    @staticmethod
    def list_agents(
        info: Info[GraphQLContext, None],
        team_id: strawberry.ID,
        page: int = 0,
        page_size: int = 20,
    ) -> list[Agent]:
        from .types import Agent

        user_id = info.context.user_id

        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        agents = metadb.list_agents_by_team_id(
            team_id=uuid.UUID(team_id),
            page=page,
            page_size=page_size,
        )

        return [
            Agent(
                id=a.uuid,
                org_id=a.org_id,
                team_id=a.team_id,
                user_id=a.user_id,
                name=a.name,
                type=GraphQLAgentTypeEnum[AgentType(a.type).name],
                description=a.description,
                meta=a.meta,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in agents
        ]

    @staticmethod
    def get_agent(info: Info[GraphQLContext, None], id: strawberry.ID) -> Agent | None:
        from .types import Agent

        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.agent_is_accessible_to_user(agent_id=id, user_id=user_id):
            raise RuntimeError(
                "Not allowed to access agent that user does not belong to"
            )

        agent = metadb.get_agent(agent_id=uuid.UUID(id))
        if agent:
            return Agent(
                id=agent.uuid,
                org_id=agent.org_id,
                team_id=agent.team_id,
                user_id=agent.user_id,
                name=agent.name,
                type=GraphQLAgentTypeEnum[AgentType(agent.type).name],
                description=agent.description,
                meta=agent.meta,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
            )
        return None

    @staticmethod
    def get_session(
        info: Info[GraphQLContext, None], id: strawberry.ID
    ) -> Session | None:
        from .types import Session

        user_id = info.context.user_id

        metadb = runtime.storage_runtime().metadb
        if not metadb.session_is_accessible_to_user(session_id=id, user_id=user_id):
            raise RuntimeError(
                "Not allowed to access session that user does not belong to"
            )

        session = metadb.get_session(session_id=id)
        if session:
            return Session(
                id=session.uuid,
                org_id=session.org_id,
                agent_id=session.agent_id,
                team_id=session.team_id,
                user_id=session.user_id,
                meta=session.meta,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
        return None

    @staticmethod
    def list_sessions_by_agent_id(
        info: Info[GraphQLContext, None],
        agent_id: strawberry.ID,
        page: int = 0,
        page_size: int = 10,
    ) -> list[Session]:
        from .types import Session

        user_id = info.context.user_id

        metadb = runtime.storage_runtime().metadb
        if not metadb.agent_is_accessible_to_user(agent_id=agent_id, user_id=user_id):
            raise RuntimeError(
                "Not allowed to access agent that user does not belong to"
            )

        sessions = metadb.list_sessions_by_agent_id(
            agent_id=agent_id,
            page=page,
            page_size=page_size,
        )
        return [
            Session(
                id=s.uuid,
                org_id=s.org_id,
                agent_id=s.agent_id,
                team_id=s.team_id,
                user_id=s.user_id,
                meta=s.meta,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ]

    @staticmethod
    def list_runs_by_session_id(
        info: Info[GraphQLContext, None],
        session_id: strawberry.ID,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Run]:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.session_is_accessible_to_user(
            session_id=session_id, user_id=user_id
        ):
            raise RuntimeError(
                "Not allowed to access session that user does not belong to"
            )

        runs = metadb.list_runs_by_session_id(
            session_id=session_id,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
        )
        return [
            Run(
                id=str(r.uuid),
                org_id=str(r.org_id),
                team_id=str(r.team_id),
                user_id=str(r.user_id),
                experiment_id=str(r.experiment_id) if r.experiment_id else None,
                session_id=str(r.session_id) if r.session_id else None,
                meta=r.meta,
                status=GraphQLStatusEnum[Status(r.status).name],
                duration=r.duration,
                created_at=r.created_at,
            )
            for r in runs
        ]

    @staticmethod
    def total_agents(info: Info[GraphQLContext, None], team_id: strawberry.ID) -> int:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        return metadb.count_agents(team_id=team_id)

    @staticmethod
    def total_sessions(info: Info[GraphQLContext, None], team_id: strawberry.ID) -> int:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )
        return metadb.count_sessions(team_id=team_id)

    @staticmethod
    def list_exp_metrics(
        info: Info[GraphQLContext, None], experiment_id: strawberry.ID
    ) -> list[Metric]:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.experiment_is_accessible_to_user(
            experiment_id=experiment_id, user_id=user_id
        ):
            raise RuntimeError(
                "Not allowed to access experiment that user does not belong to"
            )

        metrics = metadb.list_metrics_by_experiment_id(experiment_id=experiment_id)
        return [
            Metric(
                id=m.uuid,
                org_id=m.org_id,
                key=m.key,
                value=m.value,
                team_id=m.team_id,
                experiment_id=m.experiment_id,
                run_id=m.run_id,
                created_at=m.created_at,
            )
            for m in metrics
        ]

    @staticmethod
    def list_run_metrics(
        info: Info[GraphQLContext, None], run_id: strawberry.ID
    ) -> list[Metric]:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.run_is_accessible_to_user(run_id=run_id, user_id=user_id):
            raise RuntimeError("Not allowed to access run that user does not belong to")

        metrics = metadb.list_metrics_by_run_id(run_id=run_id)
        return [
            Metric(
                id=m.uuid,
                org_id=m.org_id,
                key=m.key,
                value=m.value,
                team_id=m.team_id,
                experiment_id=m.experiment_id,
                run_id=m.run_id,
                created_at=m.created_at,
            )
            for m in metrics
        ]

    @staticmethod
    def total_experiments(
        info: Info[GraphQLContext, None], team_id: strawberry.ID
    ) -> int:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        return metadb.count_experiments(team_id=team_id)

    @staticmethod
    def total_runs(info: Info[GraphQLContext, None], team_id: strawberry.ID) -> int:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        return metadb.count_runs(team_id=team_id)

    @staticmethod
    def total_datasets(info: Info[GraphQLContext, None], team_id: strawberry.ID) -> int:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        return metadb.count_datasets(team_id=team_id)

    @staticmethod
    def aggregate_team_usage(
        info: Info[GraphQLContext, None], team_id: strawberry.ID
    ) -> dict[str, int | float]:
        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "total_cost": 0.0,
            }

        org_id = uuid.UUID(info.context.org_id)
        user_id = uuid.UUID(info.context.user_id)
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=org_id
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        trace_store = runtime.storage_runtime().tracestore
        result = trace_store.get_llm_usage_by_team_id(org_id=org_id, team_id=team_id)
        if result and len(result) > 0:
            return result[0]
        return {
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "total_cost": 0.0,
        }

    @staticmethod
    def aggregate_agent_usage(
        info: Info[GraphQLContext, None], agent_id: strawberry.ID
    ) -> dict[str, int | float]:
        """Aggregate token usage from all spans for an agent."""
        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "total_cost": 0.0,
            }

        ctx = info.context
        org_id = uuid.UUID(ctx.org_id)
        user_id = uuid.UUID(ctx.user_id)
        metadb = runtime.storage_runtime().metadb
        agent = metadb.get_agent(agent_id=agent_id)
        if not metadb.agent_is_accessible_to_user(agent_id=agent.uuid, user_id=user_id):
            raise RuntimeError(
                "Not allowed to access agent that user does not belong to"
            )

        trace_store = runtime.storage_runtime().tracestore
        result = trace_store.get_llm_usage_by_agent_id(
            org_id=org_id, team_id=agent.team_id, agent_id=agent_id
        )
        if result and len(result) > 0:
            return result[0]
        return {
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "total_cost": 0.0,
        }

    @staticmethod
    def aggregate_session_usage(
        info: Info[GraphQLContext, None], session_id: strawberry.ID
    ) -> dict[str, int | float]:
        """Aggregate token usage from all spans for a session."""
        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "total_cost": 0.0,
            }

        ctx = info.context
        org_id = uuid.UUID(ctx.org_id)
        user_id = uuid.UUID(ctx.user_id)
        metadb = runtime.storage_runtime().metadb
        session = metadb.get_session(session_id=session_id)
        if not metadb.session_is_accessible_to_user(
            session_id=session.uuid, user_id=user_id
        ):
            raise RuntimeError(
                "Not allowed to access session that user does not belong to"
            )

        trace_store = runtime.storage_runtime().tracestore
        result = trace_store.get_llm_usage_by_session_id(
            org_id=org_id, team_id=session.team_id, session_id=session.uuid
        )
        if result and len(result) > 0:
            return result[0]
        return {
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "total_cost": 0.0,
        }

    @staticmethod
    def aggregate_model_distributions(
        info: Info[GraphQLContext, None],
        team_id: strawberry.ID,
    ) -> list[ModelDistribution]:
        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return []

        ctx = info.context
        org_id = uuid.UUID(ctx.org_id)
        user_id = uuid.UUID(ctx.user_id)
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=org_id
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        trace_store = runtime.storage_runtime().tracestore
        result = trace_store.get_model_distributions_by_team_id(
            org_id=org_id, team_id=team_id
        )
        return [
            ModelDistribution(model=item["model"], count=item["count"])
            for item in result
        ]

    @staticmethod
    def list_exps_by_timeframe(
        info: Info[GraphQLContext, None],
        team_id: strawberry.ID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Experiment]:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        experiments = metadb.list_exps_by_timeframe(
            team_id=team_id,
            start_time=start_time,
            end_time=end_time,
        )
        return [
            # TODO: use a helper function to convert SQLAlchemy model to GraphQL type
            Experiment(
                id=e.uuid,
                org_id=e.org_id,
                team_id=e.team_id,
                user_id=e.user_id,
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
            for e in experiments
        ]

    @staticmethod
    # TODO: isolated by team_id for multi-tenancy.
    async def list_artifact_repositories(
        info: Info[GraphQLContext, None],
    ) -> list[ArtifactRepository]:
        """List all repositories in the ORAS registry."""

        registry_url = artifact.get_registry_url()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{registry_url}/v2/_catalog",
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                repositories = data.get("repositories", [])
                return [ArtifactRepository(name=repo) for repo in repositories]
            except httpx.HTTPError as e:
                raise RuntimeError(f"Registry request failed: {e}") from e

    @staticmethod
    async def list_artifact_tags(
        info: Info[GraphQLContext, None],
        team_id: str,
        repo_name: str,
    ) -> list[ArtifactTag]:
        """List tags for a repository."""
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        arf = runtime.storage_runtime().artifact
        return [
            ArtifactTag(name=tag) for tag in arf.list_versions(f"{team_id}/{repo_name}")
        ]

    @staticmethod
    async def list_artifact_files(
        info: Info[GraphQLContext, None], team_id: str, tag: str, repo_name: str
    ) -> list[ArtifactFile]:
        """List files in an artifact without loading content."""
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        try:
            arf = runtime.storage_runtime().artifact
            file_paths = arf.pull(repo_name=f"{team_id}/{repo_name}", version=tag)

            if not file_paths:
                return []

            files = []
            for file_path in file_paths:
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)

                # Determine content type based on file extension
                if filename.endswith(".json"):
                    content_type = "application/json"
                elif (
                    filename.endswith(".txt")
                    or filename.endswith(".log")
                    or filename.endswith((".py", ".js", ".ts", ".tsx", ".jsx"))
                ):
                    content_type = "text/plain"
                else:
                    content_type = "text/plain"

                files.append(
                    ArtifactFile(
                        filename=filename, size=file_size, content_type=content_type
                    )
                )

            return files
        except Exception as e:
            raise RuntimeError(f"Failed to list artifact files: {e}") from e

    @staticmethod
    async def get_artifact_content(
        info: Info[GraphQLContext, None],
        team_id: str,
        tag: str,
        repo_name: str | None = None,
        filename: str | None = None,
    ) -> ArtifactContent | None:
        """Get artifact content from registry."""
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        try:
            # Initialize artifact client
            arf = runtime.storage_runtime().artifact

            # Pull the artifact - ORAS will manage temp directory
            # Returns absolute paths to files in ORAS temp directory
            file_paths = arf.pull(repo_name=f"{team_id}/{repo_name}", version=tag)

            if not file_paths:
                raise RuntimeError("No files found in artifact")

            # Find the requested file or use first file
            file_path = None
            if filename:
                for path in file_paths:
                    if os.path.basename(path) == filename:
                        file_path = path
                        break
                if not file_path:
                    raise RuntimeError(f"File '{filename}' not found in artifact")
            else:
                file_path = file_paths[0]

            # Read file content
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Get filename from path
            actual_filename = os.path.basename(file_path)

            # Determine content type based on file extension
            if actual_filename.endswith(".json"):
                content_type = "application/json"
            elif (
                actual_filename.endswith(".txt")
                or actual_filename.endswith(".log")
                or actual_filename.endswith((".py", ".js", ".ts", ".tsx", ".jsx"))
            ):
                content_type = "text/plain"
            else:
                content_type = "text/plain"

            return ArtifactContent(
                filename=actual_filename, content=content, content_type=content_type
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get artifact content: {e}") from e

    @staticmethod
    def aggregate_run_usage(
        info: Info[GraphQLContext, None], run_id: strawberry.ID
    ) -> dict[str, int | float]:
        """Aggregate token usage from all traces for a run."""

        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "total_cost": 0.0,
            }

        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.run_is_accessible_to_user(run_id=run_id, user_id=user_id):
            raise RuntimeError("Not allowed to access run that user does not belong to")

        return GraphQLResolvers.get_run_usage(info, run_id)

    @staticmethod
    def get_run_usage(
        info: Info[GraphQLContext, None], run_id: strawberry.ID
    ) -> dict[str, float]:
        ctx = info.context
        org_id = uuid.UUID(ctx.org_id)
        run = runtime.storage_runtime().metadb.get_run(run_id=run_id)

        trace_store = runtime.storage_runtime().tracestore
        spans = trace_store.get_llm_spans_by_run_id(
            org_id=org_id, team_id=run.team_id, run_id=uuid.UUID(run_id)
        )
        # Don't close - it's a shared singleton connection

        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        cache_read_input_tokens = 0
        cache_creation_input_tokens = 0
        total_cost = 0.0

        for span in spans:
            span_attrs = span.get("SpanAttributes", {})

            # Aggregate tokens from LLM spans
            if "llm.usage.total_tokens" in span_attrs:
                total_tokens += int(span_attrs["llm.usage.total_tokens"])
            if "gen_ai.usage.input_tokens" in span_attrs:
                input_tokens += int(span_attrs["gen_ai.usage.input_tokens"])
            if "gen_ai.usage.output_tokens" in span_attrs:
                output_tokens += int(span_attrs["gen_ai.usage.output_tokens"])
            if "gen_ai.usage.cache_read_input_tokens" in span_attrs:
                cache_read_input_tokens += int(
                    span_attrs["gen_ai.usage.cache_read_input_tokens"]
                )
            if "gen_ai.usage.cache_creation_input_tokens" in span_attrs:
                cache_creation_input_tokens += int(
                    span_attrs["gen_ai.usage.cache_creation_input_tokens"]
                )
            if "alphatrion.cost.total_tokens" in span_attrs:
                total_cost += float(span_attrs["alphatrion.cost.total_tokens"])

        return {
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read_input_tokens,
            "cache_creation_input_tokens": cache_creation_input_tokens,
            "total_cost": total_cost,
        }

    @staticmethod
    def aggregate_experiment_usage(
        info: Info[GraphQLContext, None], experiment_id: strawberry.ID
    ) -> dict[str, int | float]:
        """Aggregate token usage from all spans in an experiment."""
        org_id = info.context.org_id
        user_id = info.context.user_id

        metadb = runtime.storage_runtime().metadb
        if not metadb.experiment_is_accessible_to_user(
            experiment_id=experiment_id, user_id=user_id
        ):
            raise RuntimeError(
                "Not allowed to access experiment that user does not belong to"
            )

        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "total_cost": 0.0,
            }

        exp = runtime.storage_runtime().metadb.get_experiment(
            experiment_id=experiment_id
        )
        return GraphQLResolvers.get_experiment_usage(org_id, exp.team_id, experiment_id)

    @staticmethod
    def get_experiment_usage(
        org_id: strawberry.ID, team_id: strawberry.ID, experiment_id: strawberry.ID
    ) -> tuple[dict[str, int], dict[str, float]]:
        trace_store = runtime.storage_runtime().tracestore
        # Get all LLM spans for this experiment in a single query
        spans = trace_store.get_llm_spans_by_exp_id(
            org_id=org_id, team_id=team_id, experiment_id=experiment_id
        )
        # Don't close - it's a shared singleton connection

        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        cache_read_input_tokens = 0
        cache_creation_input_tokens = 0
        total_cost = 0.0

        for span in spans:
            span_attrs = span.get("SpanAttributes", {})

            # Aggregate tokens from LLM spans
            if "llm.usage.total_tokens" in span_attrs:
                total_tokens += int(span_attrs["llm.usage.total_tokens"])
            if "gen_ai.usage.input_tokens" in span_attrs:
                input_tokens += int(span_attrs["gen_ai.usage.input_tokens"])
            if "gen_ai.usage.output_tokens" in span_attrs:
                output_tokens += int(span_attrs["gen_ai.usage.output_tokens"])
            if "gen_ai.usage.cache_read_input_tokens" in span_attrs:
                cache_read_input_tokens += int(
                    span_attrs["gen_ai.usage.cache_read_input_tokens"]
                )
            if "gen_ai.usage.cache_creation_input_tokens" in span_attrs:
                cache_creation_input_tokens += int(
                    span_attrs["gen_ai.usage.cache_creation_input_tokens"]
                )
            if "alphatrion.cost.total_tokens" in span_attrs:
                total_cost += float(span_attrs["alphatrion.cost.total_tokens"])

        return {
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read_input_tokens,
            "cache_creation_input_tokens": cache_creation_input_tokens,
            "total_cost": total_cost,
        }

    @staticmethod
    def list_spans_by_run_id(
        info: Info[GraphQLContext, None], run_id: strawberry.ID
    ) -> list[Span]:
        """List all spans for a specific run."""

        # Check if tracing is enabled
        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return []

        try:
            ctx = info.context
            org_id = uuid.UUID(ctx.org_id)
            run = runtime.storage_runtime().metadb.get_run(run_id=run_id)

            trace_store = runtime.storage_runtime().tracestore

            # Get traces from ClickHouse
            raw_spans = trace_store.get_spans_by_run_id(
                org_id=org_id, team_id=run.team_id, run_id=uuid.UUID(run_id)
            )
            # Don't close - it's a shared singleton connection

            # Convert to GraphQL Span objects
            spans = []
            for t in raw_spans:
                # Convert events from ClickHouse flat arrays
                events = []
                event_timestamps = t.get("EventTimestamps", [])
                event_names = t.get("EventNames", [])
                event_attrs = t.get("EventAttributes", [])
                for i in range(len(event_names)):
                    events.append(
                        TraceEvent(
                            timestamp=event_timestamps[i]
                            if i < len(event_timestamps)
                            else datetime.now(),
                            name=event_names[i],
                            attributes=event_attrs[i] if i < len(event_attrs) else {},
                        )
                    )

                # Convert links from ClickHouse flat arrays
                links = []
                link_trace_ids = t.get("LinkTraceIds", [])
                link_span_ids = t.get("LinkSpanIds", [])
                link_attrs = t.get("LinkAttributes", [])
                for i in range(len(link_trace_ids)):
                    links.append(
                        TraceLink(
                            trace_id=link_trace_ids[i],
                            span_id=link_span_ids[i] if i < len(link_span_ids) else "",
                            attributes=link_attrs[i] if i < len(link_attrs) else {},
                        )
                    )

                spans.append(
                    Span(
                        timestamp=t["Timestamp"],
                        trace_id=t["TraceId"],
                        span_id=t["SpanId"],
                        parent_span_id=t["ParentSpanId"],
                        span_name=t["SpanName"],
                        span_kind=t["SpanKind"],
                        semantic_kind=t["SemanticKind"],
                        service_name=t["ServiceName"],
                        duration=t["Duration"],
                        status_code=t["StatusCode"],
                        status_message=t["StatusMessage"],
                        team_id=t["TeamId"],
                        run_id=t["RunId"],
                        experiment_id=t["ExperimentId"],
                        span_attributes=t["SpanAttributes"],
                        resource_attributes=t["ResourceAttributes"],
                        events=events,
                        links=links,
                    )
                )

            return spans
        except Exception as e:
            # Log error and return empty list - don't fail the GraphQL query
            print(f"Failed to fetch traces: {e}")
            return []

    @staticmethod
    def list_spans_by_session_id(
        info: Info[GraphQLContext, None], session_id: strawberry.ID
    ) -> list[Span]:
        """List all spans for a specific session (agent runs)."""

        # Check if tracing is enabled
        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return []

        try:
            ctx = info.context
            org_id = uuid.UUID(ctx.org_id)
            session = runtime.storage_runtime().metadb.get_session(
                session_id=session_id
            )

            trace_store = runtime.storage_runtime().tracestore

            # Get traces from ClickHouse for this session
            raw_spans = trace_store.get_spans_by_session_id(
                org_id=org_id,
                team_id=session.team_id,
                session_id=uuid.UUID(session.uuid),
            )
            # Don't close - it's a shared singleton connection

            # Convert to GraphQL Span objects
            spans = []
            for t in raw_spans:
                # Convert events from ClickHouse flat arrays
                events = []
                event_timestamps = t.get("EventTimestamps", [])
                event_names = t.get("EventNames", [])
                event_attrs = t.get("EventAttributes", [])
                for i in range(len(event_timestamps)):
                    events.append(
                        TraceEvent(
                            timestamp=event_timestamps[i],
                            name=event_names[i] if i < len(event_names) else "",
                            attributes=event_attrs[i] if i < len(event_attrs) else {},
                        )
                    )

                # Convert links from ClickHouse flat arrays
                links = []
                link_trace_ids = t.get("LinkTraceIds", [])
                link_span_ids = t.get("LinkSpanIds", [])
                link_attrs = t.get("LinkAttributes", [])
                for i in range(len(link_trace_ids)):
                    links.append(
                        TraceLink(
                            trace_id=link_trace_ids[i],
                            span_id=link_span_ids[i] if i < len(link_span_ids) else "",
                            attributes=link_attrs[i] if i < len(link_attrs) else {},
                        )
                    )

                spans.append(
                    Span(
                        timestamp=t["Timestamp"],
                        trace_id=t["TraceId"],
                        span_id=t["SpanId"],
                        parent_span_id=t["ParentSpanId"],
                        span_name=t["SpanName"],
                        span_kind=t["SpanKind"],
                        semantic_kind=t["SemanticKind"],
                        service_name=t["ServiceName"],
                        duration=t["Duration"],
                        status_code=t["StatusCode"],
                        status_message=t["StatusMessage"],
                        team_id=t["TeamId"],
                        run_id=t["RunId"],
                        experiment_id=t["ExperimentId"],
                        span_attributes=t["SpanAttributes"],
                        resource_attributes=t["ResourceAttributes"],
                        events=events,
                        links=links,
                    )
                )

            return spans
        except Exception as e:
            # Log error and return empty list - don't fail the GraphQL query
            print(f"Failed to fetch traces for session: {e}")
            return []

    @staticmethod
    def get_daily_cost_usage(
        info: Info[GraphQLContext, None], team_id: strawberry.ID, days: int = 7
    ) -> list[DailyCostUsage]:
        """Get daily cost usage from LLM calls for a team."""

        # Check if tracing is enabled
        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return []

        ctx = info.context
        org_id = uuid.UUID(ctx.org_id)
        user_id = uuid.UUID(ctx.user_id)
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=org_id
        ):
            return []

        try:
            trace_store = runtime.storage_runtime().tracestore
            daily_cost = trace_store.get_daily_cost_usage(
                org_id=org_id, team_id=team_id, days=days
            )
            # Don't close - it's a shared singleton connection

            # Convert to GraphQL DailyCostUsage objects
            return [
                DailyCostUsage(
                    date=item["date"],
                    total_cost=item["total_cost"],
                    total_tokens=item.get("total_tokens", 0),
                    input_tokens=item.get("input_tokens", 0),
                    output_tokens=item.get("output_tokens", 0),
                    cache_read_input_tokens=item.get("cache_read_input_tokens", 0),
                    cache_creation_input_tokens=item.get(
                        "cache_creation_input_tokens", 0
                    ),
                )
                for item in daily_cost
            ]
        except Exception as e:
            # Log error and return empty list - don't fail the GraphQL query
            print(f"Failed to fetch daily cost usage: {e}")
            return []

    @staticmethod
    def get_experiment_trace_stats(
        info: Info[GraphQLContext, None], experiment_id: strawberry.ID
    ) -> dict[str, int]:
        """Get trace statistics (success/error counts) for an experiment."""

        # Check if tracing is enabled
        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return {"total_spans": 0, "success_spans": 0, "error_spans": 0}

        try:
            ctx = info.context
            org_id = uuid.UUID(ctx.org_id)
            exp = runtime.storage_runtime().metadb.get_experiment(
                experiment_id=experiment_id
            )

            trace_store = runtime.storage_runtime().tracestore
            stats = trace_store.get_trace_stats_by_exp_id(
                org_id=org_id, team_id=exp.team_id, exp_id=experiment_id
            )
            # Don't close - it's a shared singleton connection
            return stats
        except Exception as e:
            # Log error and return zeros - don't fail the GraphQL query
            import logging

            logging.error(
                f"Failed to get trace stats for experiment {experiment_id}: {e}"
            )
            return {"total_spans": 0, "success_spans": 0, "error_spans": 0}

    @staticmethod
    def list_datasets(
        info: Info[GraphQLContext, None],
        team_id: strawberry.ID,
        experiment_id: strawberry.ID | None = None,
        run_id: strawberry.ID | None = None,
        name: str | None = None,
        page: int = 0,
        page_size: int = 20,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Dataset]:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=uuid.UUID(info.context.org_id)
        ):
            raise RuntimeError(
                "Not allowed to access team that user does not belong to"
            )

        datasets = metadb.list_datasets(
            team_id=team_id,
            experiment_id=experiment_id,
            run_id=run_id,
            name=name,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
        )
        return [
            Dataset(
                id=d.uuid,
                org_id=d.org_id,
                name=d.name,
                description=d.description,
                path=d.path,
                meta=d.meta,
                team_id=d.team_id,
                experiment_id=d.experiment_id,
                run_id=d.run_id,
                user_id=d.user_id,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in datasets
        ]

    @staticmethod
    def get_dataset(
        info: Info[GraphQLContext, None], id: strawberry.ID
    ) -> Dataset | None:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.dataset_is_accessible_to_user(dataset_id=id, user_id=user_id):
            raise RuntimeError(
                "Not allowed to access dataset that user does not belong to"
            )

        dataset = metadb.get_dataset(dataset_id=uuid.UUID(id))
        if dataset:
            return Dataset(
                id=dataset.uuid,
                org_id=dataset.org_id,
                name=dataset.name,
                description=dataset.description,
                path=dataset.path,
                meta=dataset.meta,
                team_id=dataset.team_id,
                experiment_id=dataset.experiment_id,
                run_id=dataset.run_id,
                user_id=dataset.user_id,
                created_at=dataset.created_at,
                updated_at=dataset.updated_at,
            )
        return None


class GraphQLMutations:
    @staticmethod
    def create_user(info: Info[GraphQLContext, None], input: CreateUserInput) -> User:
        org_id = info.context.org_id
        original_user_id = info.context.user_id

        metadb = runtime.storage_runtime().metadb
        if not metadb.user_is_super_admin_in_org(
            user_id=uuid.UUID(original_user_id), org_id=uuid.UUID(org_id)
        ):
            raise RuntimeError("Only super admin can create users")

        user_id = metadb.create_user(
            uuid=uuid.UUID(input.id) if input.id else None,
            org_id=uuid.UUID(input.org_id),
            name=input.name,
            email=input.email,
            avatar_url=input.avatar_url,
            meta=input.meta,
        )
        user = metadb.get_user(user_id=user_id)
        if user:
            return User(
                id=user.uuid,
                org_id=user.org_id,
                name=user.name,
                email=user.email,
                avatar_url=user.avatar_url,
                meta=user.meta,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        msg = f"Failed to create user with name {input.name}"
        raise RuntimeError(msg)

    @staticmethod
    def update_user(info: Info[GraphQLContext, None], input: UpdateUserInput) -> User:
        metadb = runtime.storage_runtime().metadb
        user_id = uuid.UUID(input.id)
        # User can only update self.
        if info.context.user_id != str(user_id):
            raise RuntimeError("It's not allowed to update other users")

        user = metadb.update_user(user_id=user_id, meta=input.meta)
        if not user:
            msg = f"User with id {input.id} not found"
            raise ValueError(msg)

        return User(
            id=user.uuid,
            org_id=user.org_id,
            name=user.name,
            email=user.email,
            avatar_url=user.avatar_url,
            meta=user.meta,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @staticmethod
    def update_organization(
        info: Info[GraphQLContext, None], input: UpdateOrganizationInput
    ) -> Organization:
        original_org_id = info.context.org_id
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.user_is_super_admin_in_org(
            user_id=uuid.UUID(user_id), org_id=uuid.UUID(original_org_id)
        ):
            raise RuntimeError("Only super admin can update organization")

        org_id = uuid.UUID(input.id)
        org = metadb.update_organization(
            org_id=org_id,
            name=input.name,
            description=input.description,
            meta=input.meta,
        )
        if not org:
            msg = f"Organization with id {input.id} not found"
            raise ValueError(msg)

        return Organization(
            id=org.uuid,
            name=org.name,
            description=org.description,
            meta=org.meta,
            created_at=org.created_at,
            updated_at=org.updated_at,
        )

    @staticmethod
    def create_team(info: Info[GraphQLContext, None], input: CreateTeamInput) -> Team:
        org_id = info.context.org_id
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.user_is_super_admin_in_org(
            user_id=uuid.UUID(user_id), org_id=uuid.UUID(org_id)
        ):
            raise RuntimeError("Only super admin can create teams")

        team_id = metadb.create_team(
            uuid=uuid.UUID(input.id) if input.id else None,
            org_id=uuid.UUID(input.org_id),
            name=input.name,
            description=input.description,
            meta=input.meta,
        )
        team = metadb.get_team(team_id=team_id)
        if team:
            return Team(
                id=team.uuid,
                org_id=team.org_id,
                name=team.name,
                description=team.description,
                meta=team.meta,
                created_at=team.created_at,
                updated_at=team.updated_at,
            )
        msg = f"Failed to create team with name {input.name}"
        raise RuntimeError(msg)

    @staticmethod
    def add_user_to_team(
        info: Info[GraphQLContext, None], input: AddUserToTeamInput
    ) -> bool:
        metadb = runtime.storage_runtime().metadb
        if not metadb.user_is_super_admin_in_org(
            user_id=uuid.UUID(info.context.user_id),
            org_id=uuid.UUID(info.context.org_id),
        ):
            raise RuntimeError("Only super admin can add users to teams")

        user_id = uuid.UUID(input.user_id)
        team_id = uuid.UUID(input.team_id)

        # Add user to team (creates TeamMember entry)
        return metadb.add_user_to_team(user_id=user_id, team_id=team_id)

    @staticmethod
    def remove_user_from_team(
        info: Info[GraphQLContext, None], input: RemoveUserFromTeamInput
    ) -> bool:
        metadb = runtime.storage_runtime().metadb

        user_id = uuid.UUID(input.user_id)
        team_id = uuid.UUID(input.team_id)

        if not metadb.team_is_accessible_to_user(
            team_id=team_id,
            user_id=uuid.UUID(info.context.user_id),
            org_id=uuid.UUID(info.context.org_id),
        ):
            raise RuntimeError(
                "Not allowed to modify team that user does not belong to"
            )

        # Remove user from team (deletes TeamMember entry)
        return metadb.remove_user_from_team(user_id=user_id, team_id=team_id)

    @staticmethod
    def create_experiment(
        info: Info[GraphQLContext, None], input: CreateExperimentInput
    ) -> Experiment:
        """Create a new experiment."""

        user_id = uuid.UUID(info.context.user_id)
        org_id = uuid.UUID(info.context.org_id)
        team_id = uuid.UUID(input.team_id)

        metadb = runtime.storage_runtime().metadb

        # Verify user has access to the team
        if not metadb.team_is_accessible_to_user(
            team_id=team_id, user_id=user_id, org_id=org_id
        ):
            raise RuntimeError(
                "Not allowed to create experiments in team that user does not belong to"
            )

        # Check if experiment with same name already exists in the team
        existing_exp = metadb.get_exp_by_name(
            name=input.name, team_id=team_id, include_deleted=True
        )
        if existing_exp:
            raise RuntimeError(
                f"Experiment with name '{input.name}' already exists in this team"
            )

        # Create experiment
        experiment_id = metadb.create_experiment(
            name=input.name,
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            description=input.description,
            labels=input.labels,
            tags=input.tags,
            meta=input.meta,
            params=input.params,
            status=Status.PENDING,
        )

        # Get the created experiment
        exp = metadb.get_experiment(experiment_id=experiment_id)
        if not exp:
            raise RuntimeError("Failed to create experiment")

        return Experiment(
            id=exp.uuid,
            org_id=exp.org_id,
            team_id=exp.team_id,
            user_id=exp.user_id,
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

    @staticmethod
    def update_experiment(
        info: Info[GraphQLContext, None], input: UpdateExperimentInput
    ) -> Experiment:
        """Update an existing experiment."""

        user_id = uuid.UUID(info.context.user_id)
        org_id = uuid.UUID(info.context.org_id)
        experiment_id = uuid.UUID(input.id)

        metadb = runtime.storage_runtime().metadb

        # Get the experiment to check if it exists
        exp = metadb.get_experiment(experiment_id=experiment_id)
        if not exp:
            raise RuntimeError(f"Experiment with id '{input.id}' not found")

        if not metadb.team_is_accessible_to_user(
            team_id=exp.team_id, user_id=user_id, org_id=org_id
        ):
            raise RuntimeError(
                "Not allowed to update experiment in team that user does not belong to"
            )

        # Build update kwargs
        update_kwargs = {}
        if input.description is not None:
            update_kwargs["description"] = input.description
        if input.meta is not None:
            update_kwargs["meta"] = input.meta
        if input.params is not None:
            update_kwargs["params"] = input.params
        if input.labels is not None:
            update_kwargs["labels"] = input.labels
        if input.tags is not None:
            update_kwargs["tags"] = input.tags

        # Update experiment
        if update_kwargs:
            metadb.update_experiment(
                experiment_id=experiment_id,
                **update_kwargs,
            )

        # Get the updated experiment
        updated_exp = metadb.get_experiment(experiment_id=experiment_id)
        if not updated_exp:
            raise RuntimeError("Failed to retrieve updated experiment")

        return Experiment(
            id=updated_exp.uuid,
            org_id=updated_exp.org_id,
            team_id=updated_exp.team_id,
            user_id=updated_exp.user_id,
            name=updated_exp.name,
            description=updated_exp.description,
            meta=updated_exp.meta,
            params=updated_exp.params,
            duration=updated_exp.duration,
            status=GraphQLStatusEnum[Status(updated_exp.status).name],
            kind=GraphQLExperimentTypeEnum[
                GraphQLExperimentType(updated_exp.kind).name
            ],
            created_at=updated_exp.created_at,
            updated_at=updated_exp.updated_at,
        )

    @staticmethod
    def delete_experiment(
        info: Info[GraphQLContext, None], experiment_id: strawberry.ID
    ) -> bool:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.experiment_is_accessible_to_user(
            experiment_id=experiment_id, user_id=user_id
        ):
            return False

        # Soft delete experiment by setting is_del flag
        return metadb.delete_experiment(experiment_id=experiment_id)

    @staticmethod
    def delete_experiments(
        info: Info[GraphQLContext, None], experiment_ids: list[strawberry.ID]
    ) -> int:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        # Convert strawberry IDs to UUIDs and filter by user access
        accessible_ids = []
        for exp_id in experiment_ids:
            if metadb.experiment_is_accessible_to_user(
                experiment_id=exp_id, user_id=user_id
            ):
                accessible_ids.append(uuid.UUID(exp_id))
        # Soft delete experiments by setting is_del flag
        return metadb.delete_experiments(experiment_ids=accessible_ids)

    @staticmethod
    def delete_dataset(
        info: Info[GraphQLContext, None], dataset_id: strawberry.ID
    ) -> bool:
        user_id = info.context.user_id
        metadb = runtime.storage_runtime().metadb
        if not metadb.dataset_is_accessible_to_user(
            dataset_id=dataset_id, user_id=user_id
        ):
            return False

        artifact = runtime.storage_runtime().artifact
        dataset = metadb.get_dataset(dataset_id=dataset_id)

        # delete the artifact file as well
        if dataset:
            try:
                repo_name, version = dataset.path.split(":", 1)
                artifact.delete(repo_name=repo_name, versions=version)
            except Exception as e:
                print(f"Failed to delete artifact for dataset {dataset_id}: {e}")

        return metadb.delete_dataset(dataset_id=dataset_id)

    @staticmethod
    def delete_datasets(
        info: Info[GraphQLContext, None], dataset_ids: list[strawberry.ID]
    ) -> bool:
        for id in dataset_ids:
            GraphQLMutations.delete_dataset(info=info, dataset_id=id)
        return True

    @staticmethod
    def abort_experiment(
        info: Info[GraphQLContext, None], experiment_id: strawberry.ID
    ) -> Experiment:
        """Abort an experiment by changing its status to ABORTED.
        Only works if the experiment is in PENDING status."""

        user_id = uuid.UUID(info.context.user_id)
        org_id = uuid.UUID(info.context.org_id)
        experiment_id_uuid = uuid.UUID(experiment_id)

        metadb = runtime.storage_runtime().metadb

        # Get the experiment to check if it exists
        exp = metadb.get_experiment(experiment_id=experiment_id_uuid)
        if not exp:
            raise RuntimeError(f"Experiment with id '{experiment_id}' not found")

        if not metadb.team_is_accessible_to_user(
            team_id=exp.team_id, user_id=user_id, org_id=org_id
        ):
            raise RuntimeError(
                "Not allowed to update experiment in team that user does not belong to"
            )

        # Only abort if experiment is in PENDING status
        if exp.status != Status.PENDING:
            raise RuntimeError(
                f"Cannot abort experiment with status '{StatusMap[Status(exp.status)]}'. "
                "Only experiments in PENDING status can be aborted."
            )

        # Update status to ABORTED
        metadb.update_experiment(
            experiment_id=experiment_id_uuid,
            status=Status.ABORTED,
        )

        # Get the updated experiment
        updated_exp = metadb.get_experiment(experiment_id=experiment_id_uuid)
        if not updated_exp:
            raise RuntimeError("Failed to retrieve aborted experiment")

        return Experiment(
            id=updated_exp.uuid,
            org_id=updated_exp.org_id,
            team_id=updated_exp.team_id,
            user_id=updated_exp.user_id,
            name=updated_exp.name,
            description=updated_exp.description,
            meta=updated_exp.meta,
            params=updated_exp.params,
            duration=updated_exp.duration,
            status=GraphQLStatusEnum[Status(updated_exp.status).name],
            kind=GraphQLExperimentTypeEnum[
                GraphQLExperimentType(updated_exp.kind).name
            ],
            created_at=updated_exp.created_at,
            updated_at=updated_exp.updated_at,
        )
