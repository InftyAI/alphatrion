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
    def list_exps_by_timeframe(self, start_time: datetime, end_time: datetime) -> list["Experiment"]:
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
    team_id: strawberry.ID
    meta: JSON | None
    created_at: datetime
    updated_at: datetime


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

    @strawberry.field
    def metrics(self) -> list["Metric"]:
        from .resolvers import GraphQLResolvers
        return GraphQLResolvers.list_exp_metrics(experiment_id=self.id)


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
