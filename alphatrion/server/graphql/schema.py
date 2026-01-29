import strawberry

from alphatrion.server.graphql.resolvers import GraphQLResolvers
from alphatrion.server.graphql.types import Experiment, Metric, Project, Run, Team


@strawberry.type
class Query:
    teams: list[Team] = strawberry.field(resolver=GraphQLResolvers.list_teams)
    team: Team | None = strawberry.field(resolver=GraphQLResolvers.get_team)

    @strawberry.field
    def projects(
        self,
        team_id: str,
        page: int = 0,
        page_size: int = 10,
    ) -> list[Project]:
        return GraphQLResolvers.list_projects(
            team_id=team_id, page=page, page_size=page_size
        )

    project: Project | None = strawberry.field(resolver=GraphQLResolvers.get_project)

    @strawberry.field
    def experiments(
        self, project_id: str, page: int = 0, page_size: int = 10
    ) -> list[Experiment]:
        return GraphQLResolvers.list_experiments(
            project_id=project_id, page=page, page_size=page_size
        )

    experiment: Experiment | None = strawberry.field(
        resolver=GraphQLResolvers.get_experiment
    )

    @strawberry.field
    def runs(self, experiment_id: str, page: int = 0, page_size: int = 10) -> list[Run]:
        return GraphQLResolvers.list_runs(
            experiment_id=experiment_id, page=page, page_size=page_size
        )

    run: Run | None = strawberry.field(resolver=GraphQLResolvers.get_run)

    trial_metrics: list[Metric] = strawberry.field(
        resolver=GraphQLResolvers.list_exp_metrics
    )


schema = strawberry.Schema(Query)
