from datetime import datetime

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class Project:
    id: strawberry.ID
    name: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Experiment:
    id: strawberry.ID
    project_id: strawberry.ID | None
    name: str | None
    description: str | None
    meta: JSON | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Trial:
    id: strawberry.ID
    experiment_id: strawberry.ID
    meta: JSON | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Run:
    id: strawberry.ID
    trial_id: strawberry.ID
    meta: JSON | None
    created_at: datetime


@strawberry.type
class Metric:
    id: strawberry.ID
    name: str | None
    value: float | None
    created_at: datetime
