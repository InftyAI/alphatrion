# ruff: noqa: PLC0415
from datetime import datetime
from enum import Enum

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class Team:
    id: strawberry.ID
    name: str | None
    description: str | None
    meta: JSON | None
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    def total_projects(self) -> int:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.total_projects(team_id=self.id)

    @strawberry.field
    def total_experiments(self) -> int:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.total_experiments(team_id=self.id)

    @strawberry.field
    def total_runs(self) -> int:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.total_runs(team_id=self.id)

    @strawberry.field
    def list_exps_by_timeframe(
        self, start_time: datetime, end_time: datetime
    ) -> list["Experiment"]:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.list_exps_by_timeframe(
            team_id=self.id,
            start_time=start_time,
            end_time=end_time,
        )


@strawberry.type
class User:
    id: strawberry.ID
    username: str
    email: str
    avatar_url: str | None
    meta: JSON | None
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    def teams(self) -> list["Team"] | None:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.list_teams(user_id=self.id)


@strawberry.type
class Project:
    id: strawberry.ID
    team_id: strawberry.ID
    creator_id: strawberry.ID
    name: str | None
    description: str | None
    meta: JSON | None
    created_at: datetime
    updated_at: datetime


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


@strawberry.type
class Experiment:
    id: strawberry.ID
    team_id: strawberry.ID
    user_id: strawberry.ID
    project_id: strawberry.ID
    name: str
    description: str | None
    kind: GraphQLExperimentTypeEnum
    meta: JSON | None
    params: JSON | None
    duration: float
    status: GraphQLStatusEnum
    created_at: datetime
    updated_at: datetime

    _token_cache: strawberry.Private[dict[str, int] | None] = None

    @strawberry.field
    def metrics(self) -> list["Metric"]:
        from .resolvers import GraphQLResolvers

        return GraphQLResolvers.list_exp_metrics(experiment_id=self.id)

    def _get_token_data(self) -> dict[str, int]:
        """Get token data with caching to avoid multiple ClickHouse queries."""
        if self._token_cache is None:
            from .resolvers import GraphQLResolvers

            self._token_cache = GraphQLResolvers.aggregate_experiment_tokens(
                experiment_id=self.id
            )
        return self._token_cache

    @strawberry.field
    def total_tokens(self) -> int:
        """Get total token usage from ClickHouse."""
        return self._get_token_data()["total_tokens"]

    @strawberry.field
    def input_tokens(self) -> int:
        """Get input token usage from ClickHouse."""
        return self._get_token_data()["input_tokens"]

    @strawberry.field
    def output_tokens(self) -> int:
        """Get output token usage from ClickHouse."""
        return self._get_token_data()["output_tokens"]


@strawberry.type
class Run:
    id: strawberry.ID
    team_id: strawberry.ID
    user_id: strawberry.ID
    project_id: strawberry.ID
    experiment_id: strawberry.ID
    meta: JSON | None
    status: GraphQLStatusEnum
    created_at: datetime

    _token_cache: strawberry.Private[dict[str, int] | None] = None

    @strawberry.field
    def metrics(self) -> list["Metric"]:
        """Get metrics for this run."""
        from alphatrion.server.graphql.resolvers import GraphQLResolvers

        return GraphQLResolvers.list_run_metrics(run_id=self.id)

    @strawberry.field
    def spans(self) -> list["Span"]:
        """Get spans for this run."""
        from alphatrion.server.graphql.resolvers import GraphQLResolvers

        return GraphQLResolvers.list_spans(run_id=str(self.id))

    def _get_token_data(self) -> dict[str, int]:
        """Get token data with caching to avoid multiple ClickHouse queries."""
        if self._token_cache is None:
            from alphatrion.server.graphql.resolvers import GraphQLResolvers

            self._token_cache = GraphQLResolvers.aggregate_run_tokens(run_id=self.id)
        return self._token_cache

    @strawberry.field
    def total_tokens(self) -> int:
        """Get total token usage from ClickHouse."""
        return self._get_token_data()["total_tokens"]

    @strawberry.field
    def input_tokens(self) -> int:
        """Get input token usage from ClickHouse."""
        return self._get_token_data()["input_tokens"]

    @strawberry.field
    def output_tokens(self) -> int:
        """Get output token usage from ClickHouse."""
        return self._get_token_data()["output_tokens"]


@strawberry.type
class Metric:
    id: strawberry.ID
    key: str | None
    value: float | None
    team_id: strawberry.ID
    project_id: strawberry.ID
    experiment_id: strawberry.ID
    run_id: strawberry.ID
    created_at: datetime


# Input types for mutations
@strawberry.input
class CreateUserInput:
    id: strawberry.ID | None = None
    username: str
    email: str
    avatar_url: str | None = None
    meta: JSON | None = None


@strawberry.input
class CreateTeamInput:
    id: strawberry.ID | None = None
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
    project_id: str
    run_id: str
    experiment_id: str

    span_attributes: JSON
    resource_attributes: JSON
    events: list[TraceEvent]
    links: list[TraceLink]


@strawberry.type
class DailyTokenUsage:
    date: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
