import strawberry

from .resolvers import GraphQLResolvers
from .types import Experiment, Metric, Project, Run, Trial


@strawberry.type
class Query:
    projects: list[Project] = strawberry.field(resolver=GraphQLResolvers.list_projects)
    project: Project | None = strawberry.field(resolver=GraphQLResolvers.get_project)

    experiments: list[Experiment] = strawberry.field(
        resolver=GraphQLResolvers.list_experiments
    )
    experiment: Experiment | None = strawberry.field(
        resolver=GraphQLResolvers.get_experiment
    )

    trials: list[Trial] = strawberry.field(resolver=GraphQLResolvers.list_trials)
    trial: Trial | None = strawberry.field(resolver=GraphQLResolvers.get_trial)

    runs: list[Run] = strawberry.field(resolver=GraphQLResolvers.list_runs)
    run: Run | None = strawberry.field(resolver=GraphQLResolvers.get_run)

    trial_metrics: list[Metric] = strawberry.field(
        resolver=GraphQLResolvers.list_trial_metrics
    )


schema = strawberry.Schema(Query)
