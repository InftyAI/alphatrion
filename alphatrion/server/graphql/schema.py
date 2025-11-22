import strawberry

from alphatrion.server.graphql.resolvers import GraphQLResolvers
from alphatrion.server.graphql.types import Experiment, Metric, Project, Run, Trial


@strawberry.type
class Query:
    projects: list[Project] = strawberry.field(resolver=GraphQLResolvers.list_projects)
    project: Project | None = strawberry.field(resolver=GraphQLResolvers.get_project)

    @strawberry.field
    def experiments(
        self,
        project_id: str,
        page: int = 0,
        page_size: int = 10,
    ) -> list[Experiment]:
        return GraphQLResolvers.list_experiments(
            project_id=project_id, page=page, page_size=page_size
        )

    experiment: Experiment | None = strawberry.field(
        resolver=GraphQLResolvers.get_experiment
    )

    @strawberry.field
    def trials(
        self, experiment_id: str, page: int = 0, page_size: int = 10
    ) -> list[Trial]:
        return GraphQLResolvers.list_trials(
            experiment_id=experiment_id, page=page, page_size=page_size
        )

    trial: Trial | None = strawberry.field(resolver=GraphQLResolvers.get_trial)

    @strawberry.field
    def runs(self, trial_id: str, page: int = 0, page_size: int = 10) -> list[Run]:
        return GraphQLResolvers.list_runs(
            trial_id=trial_id, page=page, page_size=page_size
        )

    run: Run | None = strawberry.field(resolver=GraphQLResolvers.get_run)

    trial_metrics: list[Metric] = strawberry.field(
        resolver=GraphQLResolvers.list_trial_metrics
    )


schema = strawberry.Schema(Query)
