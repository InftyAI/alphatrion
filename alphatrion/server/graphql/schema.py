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
    Metric,
    RemoveUserFromTeamInput,
    Run,
    Span,
    Team,
    ExperimentFitnessSummary,
    UpdateUserInput,
    User,
    ContentSnapshot,
    ContentSnapshotSummary,
    RepoFileContent,
    RepoFileTree,
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

    @strawberry.field
    def content_snapshots(
        self, experiment_id: strawberry.ID, page: int = 0, page_size: int = 200
    ) -> list[ContentSnapshot]:
        return GraphQLResolvers.list_content_snapshots(
            trial_id=str(experiment_id), page=page, page_size=page_size
        )

    @strawberry.field
    def content_snapshots_summary(
        self, experiment_id: strawberry.ID, page: int = 0, page_size: int = 2000
    ) -> list[ContentSnapshotSummary]:
        """Lightweight content snapshots without content_text for charts."""
        return GraphQLResolvers.list_content_snapshots_summary(
            trial_id=str(experiment_id), page=page, page_size=page_size
        )

    content_snapshot: ContentSnapshot | None = strawberry.field(
        resolver=GraphQLResolvers.get_content_snapshot
    )

    @strawberry.field
    def batch_trial_fitness(
        self, trial_ids: list[str]
    ) -> list[ExperimentFitnessSummary]:
        """Batch-fetch fitness values for multiple experiments in one query."""
        return GraphQLResolvers.batch_trial_fitness(trial_ids=trial_ids)

    @strawberry.field
    def content_lineage(
        self, experiment_id: strawberry.ID, content_uid: str
    ) -> list[ContentSnapshot]:
        return GraphQLResolvers.get_content_lineage(
            trial_id=str(experiment_id), content_uid=content_uid
        )

    # WILL BE DEPRECATED --- IGNORE ---

    @strawberry.field
    def repo_file_tree(self, experiment_id: strawberry.ID) -> RepoFileTree:
        """Get the file tree structure for an experiment's repository."""
        return GraphQLResolvers.get_repo_file_tree(trial_id=str(experiment_id))

    @strawberry.field
    def repo_file_content(self, experiment_id: strawberry.ID, file_path: str) -> RepoFileContent:
        """Get the content of a specific file from an experiment's repository."""
        return GraphQLResolvers.get_repo_file_content(
            trial_id=str(experiment_id), file_path=file_path
        )

    @strawberry.field
    def local_repo_file_tree(self, path: str) -> RepoFileTree:
        """Get the file tree structure for a local directory."""
        return GraphQLResolvers.get_local_repo_file_tree(path=path)

    @strawberry.field
    def local_repo_file_content(
        self, base_path: str, file_path: str
    ) -> RepoFileContent:
        """Get the content of a specific file from a local directory."""
        return GraphQLResolvers.get_local_repo_file_content(
            base_path=base_path, file_path=file_path
        )

    @strawberry.field
    def metric_keys(self, experiment_id: strawberry.ID) -> list[str]:
        """Get available metric keys for an experiment."""
        return GraphQLResolvers.list_metric_keys(experiment_id=str(experiment_id))

    @strawberry.field
    def metrics_by_key(
        self, experiment_id: strawberry.ID, key: str, max_points: int | None = None
    ) -> list["Metric"]:
        """Get metrics for a specific experiment filtered by key."""
        return GraphQLResolvers.list_metrics_by_key(
            experiment_id=str(experiment_id), key=key, max_points=max_points
        )


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
