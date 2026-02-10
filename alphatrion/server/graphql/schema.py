import strawberry

from alphatrion.server.graphql.resolvers import GraphQLMutations, GraphQLResolvers
from alphatrion.server.graphql.types import (
    AddUserToTeamInput,
    CreateTeamInput,
    CreateUserInput,
    Experiment,
    Project,
    RemoveUserFromTeamInput,
    Run,
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
    def projects(
        self,
        team_id: strawberry.ID,
        page: int = 0,
        page_size: int = 20,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Project]:
        return GraphQLResolvers.list_projects(
            team_id=team_id,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
        )

    project: Project | None = strawberry.field(resolver=GraphQLResolvers.get_project)

    @strawberry.field
    def experiments(
        self,
        project_id: strawberry.ID,
        page: int = 0,
        page_size: int = 20,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Experiment]:
        return GraphQLResolvers.list_experiments(
            project_id=project_id,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
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


schema = strawberry.Schema(query=Query, mutation=Mutation)
