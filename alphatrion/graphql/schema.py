import strawberry
from typing import List, Optional

from .types import Project, Experiment, Trial, Run, Metric
from .resolvers import GraphQLResolvers


@strawberry.type
class Query:
    projects: List[Project] = strawberry.field(
        resolver=GraphQLResolvers.get_projects
    )
    project: Optional[Project] = strawberry.field(
        resolver=GraphQLResolvers.get_project
    )

    experiments: List[Experiment] = strawberry.field(
        resolver=GraphQLResolvers.get_experiments
    )
    experiment: Optional[Experiment] = strawberry.field(
        resolver=GraphQLResolvers.get_experiment
    )

    trials: List[Trial] = strawberry.field(
        resolver=GraphQLResolvers.get_trials
    )
    trial: Optional[Trial] = strawberry.field(
        resolver=GraphQLResolvers.get_trial
    )

    runs: List[Run] = strawberry.field(
        resolver=GraphQLResolvers.get_runs
    )
    run: Optional[Run] = strawberry.field(
        resolver=GraphQLResolvers.get_run
    )

    trial_metrics: List[Metric] = strawberry.field(
        resolver=GraphQLResolvers.get_trial_metrics
    )


schema = strawberry.Schema(Query)
