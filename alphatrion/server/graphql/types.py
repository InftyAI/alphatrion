# ruff: noqa: PLC0415
from datetime import datetime
from enum import Enum

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info


@strawberry.type
class TokenStats:
    total_tokens: int
    input_tokens: int
    output_tokens: int


@strawberry.type
class ModelDistribution:
    model: str
    count: int


@strawberry.type
class DailyTokenUsage:
    date: str
    total_tokens: int
    input_tokens: int
    output_tokens: int


@strawberry.type
class TraceStats:
    total_spans: int
    success_spans: int
    error_spans: int


@strawberry.type
class Organization:
    id: strawberry.ID
    name: str
    description: str | None
    meta: JSON | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Team:
    id: strawberry.ID
    org_id: strawberry.ID
    name: str | None
    description: str | None
    meta: JSON | None
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    def total_experiments(self, info: Info) -> int:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.total_experiments(info=info, team_id=self.id)

    @strawberry.field
    def total_runs(self, info: Info) -> int:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.total_runs(info=info, team_id=self.id)

    @strawberry.field
    def total_datasets(self, info: Info) -> int:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.total_datasets(info=info, team_id=self.id)

    @strawberry.field
    def total_agents(self, info: Info) -> int:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.total_agents(info=info, team_id=self.id)

    @strawberry.field
    def total_sessions(self, info: Info) -> int:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.total_sessions(info=info, team_id=self.id)

    @strawberry.field
    def aggregated_tokens(self, info: Info) -> TokenStats:
        from .resolvers import GraphQLResolvers

        token_data = GraphQLResolvers.aggregate_team_tokens(info=info, team_id=self.id)
        return TokenStats(
            total_tokens=token_data["total_tokens"],
            input_tokens=token_data["input_tokens"],
            output_tokens=token_data["output_tokens"],
        )

    @strawberry.field
    def model_distributions(self, info: Info) -> list["ModelDistribution"]:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.aggregate_model_distributions(
            info=info, team_id=self.id
        )

    @strawberry.field
    def exps_by_timeframe(
        self, info: Info, start_time: datetime, end_time: datetime
    ) -> list["Experiment"]:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.list_exps_by_timeframe(
            info=info,
            team_id=self.id,
            start_time=start_time,
            end_time=end_time,
        )


@strawberry.type
class User:
    id: strawberry.ID
    org_id: strawberry.ID
    name: str
    email: str
    avatar_url: str | None
    meta: JSON | None
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    def teams(self, info: Info) -> list[Team] | None:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.list_teams(info=info, user_id=self.id)


class GraphQLStatus(Enum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


GraphQLStatusEnum = strawberry.enum(GraphQLStatus)


class GraphQLExperimentType(Enum):
    UNKNOWN = 0
    CRAFT_EXPERIMENT = 1


GraphQLExperimentTypeEnum = strawberry.enum(GraphQLExperimentType)


class GraphQLAgentType(Enum):
    CLAUDE = 1


GraphQLAgentTypeEnum = strawberry.enum(GraphQLAgentType)


@strawberry.type
class Label:
    name: str
    value: str


@strawberry.type
class Experiment:
    id: strawberry.ID
    org_id: strawberry.ID
    team_id: strawberry.ID
    user_id: strawberry.ID
    name: str
    description: str | None
    kind: GraphQLExperimentTypeEnum
    meta: JSON | None
    params: JSON | None
    duration: float
    status: GraphQLStatusEnum
    cost: JSON | None
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    def labels(self, info: Info) -> list[Label]:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.list_labels_by_exp_id(info=info, experiment_id=self.id)

    @strawberry.field
    def tags(self, info: Info) -> list[str]:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.list_tags_by_exp_id(info=info, experiment_id=self.id)

    @strawberry.field
    def metrics(self, info: Info) -> list["Metric"]:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.list_exp_metrics(info=info, experiment_id=self.id)

    @strawberry.field
    def aggregated_tokens(self, info: Info) -> TokenStats:
        from .resolvers import GraphQLResolvers

        tokens = GraphQLResolvers.aggregate_experiment_tokens(
            info=info, experiment_id=self.id
        )
        return TokenStats(
            total_tokens=tokens["total_tokens"],
            input_tokens=tokens["input_tokens"],
            output_tokens=tokens["output_tokens"],
        )

    @strawberry.field
    def trace_stats(self, info: Info) -> TraceStats:
        from .resolvers import GraphQLResolvers

        stats = GraphQLResolvers.get_experiment_trace_stats(
            info=info, experiment_id=self.id
        )
        return TraceStats(
            total_spans=stats["total_spans"],
            success_spans=stats["success_spans"],
            error_spans=stats["error_spans"],
        )


@strawberry.type
class Agent:
    id: strawberry.ID
    org_id: strawberry.ID
    team_id: strawberry.ID
    user_id: strawberry.ID
    name: str
    type: GraphQLAgentTypeEnum
    description: str | None
    meta: JSON | None
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    def sessions(
        self, info: Info, page: int = 0, page_size: int = 10
    ) -> list["Session"]:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.list_sessions_by_agent_id(
            info=info, agent_id=self.id, page=page, page_size=page_size
        )

    @strawberry.field
    def aggregated_tokens(self, info: Info) -> TokenStats:
        from .resolvers import GraphQLResolvers

        token_data = GraphQLResolvers.aggregate_agent_tokens(
            info=info, agent_id=self.id
        )
        return TokenStats(
            total_tokens=token_data["total_tokens"],
            input_tokens=token_data["input_tokens"],
            output_tokens=token_data["output_tokens"],
        )


@strawberry.type
class Session:
    id: strawberry.ID
    org_id: strawberry.ID
    agent_id: strawberry.ID
    team_id: strawberry.ID
    user_id: strawberry.ID
    meta: JSON | None
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    def runs(self, info: Info, page: int = 0, page_size: int = 10) -> list["Run"]:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.list_runs_by_session_id(
            info=info, session_id=self.id, page=page, page_size=page_size
        )

    @strawberry.field
    def aggregated_tokens(self, info: Info) -> TokenStats:
        from .resolvers import GraphQLResolvers

        token_data = GraphQLResolvers.aggregate_session_tokens(
            info=info, session_id=self.id
        )
        return TokenStats(
            total_tokens=token_data["total_tokens"],
            input_tokens=token_data["input_tokens"],
            output_tokens=token_data["output_tokens"],
        )


@strawberry.type
class Run:
    id: strawberry.ID
    org_id: strawberry.ID
    team_id: strawberry.ID
    user_id: strawberry.ID
    experiment_id: strawberry.ID | None
    session_id: strawberry.ID | None
    meta: JSON | None
    duration: float
    status: GraphQLStatusEnum
    cost: JSON | None
    created_at: datetime

    @strawberry.field
    def metrics(self, info: Info) -> list["Metric"]:
        """Get metrics for this run."""
        from alphatrion.server.graphql.resolvers import GraphQLResolvers

        return GraphQLResolvers.list_run_metrics(info=info, run_id=self.id)

    @strawberry.field
    def spans(self, info: Info) -> list["Span"]:
        """Get spans for this run."""
        from alphatrion.server.graphql.resolvers import GraphQLResolvers

        return GraphQLResolvers.list_spans_by_run_id(info=info, run_id=self.id)

    @strawberry.field
    def aggregated_tokens(self, info: Info) -> TokenStats:
        """Get aggregated token usage for this run."""
        from .resolvers import GraphQLResolvers

        token_data = GraphQLResolvers.aggregate_run_tokens(info=info, run_id=self.id)
        return TokenStats(
            total_tokens=token_data["total_tokens"],
            input_tokens=token_data["input_tokens"],
            output_tokens=token_data["output_tokens"],
        )


@strawberry.type
class Metric:
    id: strawberry.ID
    org_id: strawberry.ID
    key: str | None
    value: float | None
    team_id: strawberry.ID
    experiment_id: strawberry.ID
    run_id: strawberry.ID
    created_at: datetime


@strawberry.type
class Dataset:
    id: strawberry.ID
    org_id: strawberry.ID
    name: str
    description: str | None
    path: str
    meta: JSON | None
    team_id: strawberry.ID
    experiment_id: strawberry.ID | None
    run_id: strawberry.ID | None
    user_id: strawberry.ID
    created_at: datetime
    updated_at: datetime


@strawberry.input
class UpdateOrganizationInput:
    id: strawberry.ID
    name: str | None = None
    description: str | None = None
    meta: JSON | None = None


@strawberry.input
class CreateUserInput:
    id: strawberry.ID | None = None
    org_id: strawberry.ID
    name: str
    email: str
    avatar_url: str | None = None
    meta: JSON | None = None


@strawberry.input
class CreateTeamInput:
    id: strawberry.ID | None = None
    org_id: strawberry.ID
    name: str
    description: str | None = None
    meta: JSON | None = None


@strawberry.input
class UpdateUserInput:
    id: strawberry.ID
    meta: JSON | None = None


@strawberry.input
class AddUserToTeamInput:
    user_id: strawberry.ID
    team_id: strawberry.ID


@strawberry.input
class RemoveUserFromTeamInput:
    user_id: strawberry.ID
    team_id: strawberry.ID


# Artifact types
@strawberry.type
class ArtifactRepository:
    name: str


@strawberry.type
class ArtifactTag:
    name: str


@strawberry.type
class ArtifactFile:
    filename: str
    size: int
    content_type: str


@strawberry.type
class ArtifactContent:
    filename: str
    content: str
    content_type: str


# Trace types
@strawberry.type
class TraceEvent:
    timestamp: datetime
    name: str
    attributes: JSON


@strawberry.type
class TraceLink:
    trace_id: str
    span_id: str
    attributes: JSON


@strawberry.type
class Span:
    timestamp: datetime
    trace_id: str
    span_id: str
    parent_span_id: str
    span_name: str
    span_kind: str
    semantic_kind: str
    service_name: str
    duration: float  # nanoseconds (using float to support large int64 values)
    status_code: str
    status_message: str

    team_id: str
    run_id: str
    experiment_id: str

    span_attributes: JSON
    resource_attributes: JSON
    events: list[TraceEvent]
    links: list[TraceLink]
