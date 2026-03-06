import strawberry

from alphatrion.server.graphql.resolvers import GraphQLMutations, GraphQLResolvers
from alphatrion.server.graphql.types import (
    AddUserToTeamInput,
    ArtifactContent,
    ArtifactRepository,
    ArtifactTag,
    CreateTeamInput,
    CreateUserInput,
    DailyTokenUsage,
    Experiment,
    RemoveUserFromTeamInput,
    Run,
    Span,
    Team,
    UpdateUserInput,
    User,
)


@strawberry.type
class Query:
    teams: list[Team] = strawberry.field(resolver=GraphQLResolvers.list_teams)
    team: Team | None = strawberry.field(resolver=GraphQLResolvers.get_team)

    user: User | None = strawberry.field(resolver=GraphQLResolvers.get_user)

    @strawberry.field
    def experiments(
        self,
        team_id: strawberry.ID,
        page: int = 0,
        page_size: int = 20,
        order_by: str = "created_at",
        order_desc: bool = True,
        label_name: str | None = None,
        label_value: str | None = None,
    ) -> list[Experiment]:
        return GraphQLResolvers.list_experiments(
            team_id=team_id,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
            label_name=label_name,
            label_value=label_value,
        )

    experiment: Experiment | None = strawberry.field(
        resolver=GraphQLResolvers.get_experiment
    )

    @strawberry.field
    def runs(
        self,
        experiment_id: strawberry.ID,
        page: int = 0,
        page_size: int = 20,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Run]:
        return GraphQLResolvers.list_runs(
            experiment_id=experiment_id,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
        )

    run: Run | None = strawberry.field(resolver=GraphQLResolvers.get_run)

    # Trace queries
    @strawberry.field
    def traces(self, run_id: strawberry.ID) -> list[Span]:
        return GraphQLResolvers.list_traces(run_id=run_id)

    @strawberry.field
    def daily_token_usage(
        self, team_id: strawberry.ID, days: int = 7
    ) -> list[DailyTokenUsage]:
        return GraphQLResolvers.get_daily_token_usage(team_id=team_id, days=days)

    # Artifact queries
    @strawberry.field
    async def artifact_repos(self) -> list[ArtifactRepository]:
        return await GraphQLResolvers.list_artifact_repositories()

    @strawberry.field
    async def artifact_tags(
        self,
        team_id: strawberry.ID,
        repo_name: str,
    ) -> list[ArtifactTag]:
        return await GraphQLResolvers.list_artifact_tags(str(team_id), repo_name)

    @strawberry.field
    async def artifact_content(
        self,
        team_id: strawberry.ID,
        tag: str,
        repo_name: str,
    ) -> ArtifactContent:
        return await GraphQLResolvers.get_artifact_content(str(team_id), tag, repo_name)


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, input: CreateUserInput) -> User:
        return GraphQLMutations.create_user(input=input)

    @strawberry.mutation
    def update_user(self, input: UpdateUserInput) -> User:
        return GraphQLMutations.update_user(input=input)

    @strawberry.mutation
    def create_team(self, input: CreateTeamInput) -> Team:
        return GraphQLMutations.create_team(input=input)

    @strawberry.mutation
    def add_user_to_team(self, input: AddUserToTeamInput) -> bool:
        return GraphQLMutations.add_user_to_team(input=input)

    @strawberry.mutation
    def remove_user_from_team(self, input: RemoveUserFromTeamInput) -> bool:
        return GraphQLMutations.remove_user_from_team(input=input)

    @strawberry.mutation
    def delete_experiment(self, experiment_id: strawberry.ID) -> bool:
        return GraphQLMutations.delete_experiment(experiment_id=experiment_id)

    @strawberry.mutation
    def delete_experiments(self, experiment_ids: list[strawberry.ID]) -> int:
        return GraphQLMutations.delete_experiments(experiment_ids=experiment_ids)


schema = strawberry.Schema(query=Query, mutation=Mutation)
