import strawberry
from strawberry.scalars import JSON
from typing import Optional, Dict
from datetime import datetime


@strawberry.type
class Project:
    id: strawberry.ID
    name: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Experiment:
    id: strawberry.ID
    project_id: Optional[strawberry.ID]
    name: Optional[str]
    description: Optional[str]
    meta: Optional[JSON]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Trial:
    id: strawberry.ID
    experiment_id: strawberry.ID
    meta: Optional[JSON]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Run:
    id: strawberry.ID
    trial_id: strawberry.ID
    meta: Optional[JSON]
    created_at: datetime


@strawberry.type
class Metric:
    id: strawberry.ID
    name: Optional[str]
    value: Optional[float]
    created_at: datetime
