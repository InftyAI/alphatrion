from datetime import datetime
from enum import Enum

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class Project:
    id: strawberry.ID
    name: str | None
    description: str | None
    meta: JSON | None
    created_at: datetime
    updated_at: datetime


class GraphQLExperimentType(Enum):
    UNKNOWN = 0
    CRAFT_EXPERIMENT = 1


GraphQLExperimentTypeEnum = strawberry.enum(GraphQLExperimentType)


@strawberry.type
class Experiment:
    id: strawberry.ID
    project_id: strawberry.ID | None
    name: str | None
    kind: GraphQLExperimentTypeEnum
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


@strawberry.type
class Trial:
    id: strawberry.ID
    experiment_id: strawberry.ID
    project_id: strawberry.ID
    name: str
    description: str | None
    meta: JSON | None
    params: JSON | None
    duration: float
    status: GraphQLStatusEnum
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Run:
    id: strawberry.ID
    trial_id: strawberry.ID
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
    project_id: strawberry.ID
    experiment_id: strawberry.ID
    trial_id: strawberry.ID
    run_id: strawberry.ID
    step: int
    created_at: datetime
