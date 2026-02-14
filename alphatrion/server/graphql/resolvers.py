import os
import uuid
from datetime import datetime

import httpx
import strawberry

from alphatrion.artifact import artifact
from alphatrion.storage import runtime
from alphatrion.storage.sql_models import Status

from .types import (
    AddUserToTeamInput,
    ArtifactContent,
    ArtifactRepository,
    ArtifactTag,
    CreateTeamInput,
    CreateUserInput,
    Experiment,
    GraphQLExperimentType,
    GraphQLExperimentTypeEnum,
    GraphQLStatusEnum,
    Metric,
    Project,
    RemoveUserFromTeamInput,
    Run,
    Team,
    UpdateUserInput,
    User,
)


class GraphQLResolvers:
    @staticmethod
    def list_teams(user_id: strawberry.ID) -> list[Team]:
        metadb = runtime.storage_runtime().metadb
        teams = metadb.list_user_teams(user_id=user_id)
        return [
            Team(
                id=t.uuid,
                name=t.name,
                description=t.description,
                meta=t.meta,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in teams
        ]

    @staticmethod
    def get_team(id: strawberry.ID) -> Team | None:
        metadb = runtime.storage_runtime().metadb
        team = metadb.get_team(team_id=uuid.UUID(id))
        if team:
            return Team(
                id=team.uuid,
                name=team.name,
                description=team.description,
                meta=team.meta,
                created_at=team.created_at,
                updated_at=team.updated_at,
            )
        return None

    @staticmethod
    def get_user(id: strawberry.ID) -> User | None:
        metadb = runtime.storage_runtime().metadb
        user = metadb.get_user(user_id=uuid.UUID(id))
        if user:
            return User(
                id=user.uuid,
                username=user.username,
                email=user.email,
                avatar_url=user.avatar_url,
                meta=user.meta,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        return None

    @staticmethod
    def list_projects(
        team_id: strawberry.ID,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Project]:
        metadb = runtime.storage_runtime().metadb
        projects = metadb.list_projects(
            team_id=uuid.UUID(team_id),
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
        )
        return [
            Project(
                id=proj.uuid,
                team_id=proj.team_id,
                creator_id=proj.creator_id,
                name=proj.name,
                description=proj.description,
                meta=proj.meta,
                created_at=proj.created_at,
                updated_at=proj.updated_at,
            )
            for proj in projects
        ]

    @staticmethod
    def get_project(id: strawberry.ID) -> Project | None:
        metadb = runtime.storage_runtime().metadb
        proj = metadb.get_project(project_id=uuid.UUID(id))
        if proj:
            return Project(
                id=proj.uuid,
                team_id=proj.team_id,
                creator_id=proj.creator_id,
                name=proj.name,
                description=proj.description,
                meta=proj.meta,
                created_at=proj.created_at,
                updated_at=proj.updated_at,
            )
        return None

    @staticmethod
    def list_experiments(
        project_id: strawberry.ID,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Experiment]:
        metadb = runtime.storage_runtime().metadb
        exps = metadb.list_exps_by_project_id(
            project_id=uuid.UUID(project_id),
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
        )
        return [
            Experiment(
                id=e.uuid,
                team_id=e.team_id,
                user_id=e.user_id,
                project_id=e.project_id,
                name=e.name,
                description=e.description,
                meta=e.meta,
                params=e.params,
                duration=e.duration,
                status=GraphQLStatusEnum[Status(e.status).name],
                kind=GraphQLExperimentTypeEnum[GraphQLExperimentType(e.kind).name],
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in exps
        ]

    @staticmethod
    def get_experiment(id: strawberry.ID) -> Experiment | None:
        metadb = runtime.storage_runtime().metadb
        exp = metadb.get_experiment(experiment_id=uuid.UUID(id))
        if exp:
            return Experiment(
                id=exp.uuid,
                team_id=exp.team_id,
                user_id=exp.user_id,
                project_id=exp.project_id,
                name=exp.name,
                description=exp.description,
                meta=exp.meta,
                params=exp.params,
                duration=exp.duration,
                status=GraphQLStatusEnum[Status(exp.status).name],
                kind=GraphQLExperimentTypeEnum[GraphQLExperimentType(exp.kind).name],
                created_at=exp.created_at,
                updated_at=exp.updated_at,
            )
        return None

    @staticmethod
    def list_runs(
        experiment_id: strawberry.ID,
        page: int = 0,
        page_size: int = 10,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Run]:
        metadb = runtime.storage_runtime().metadb
        runs = metadb.list_runs_by_exp_id(
            exp_id=uuid.UUID(experiment_id),
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc,
        )
        return [
            Run(
                id=r.uuid,
                team_id=r.team_id,
                user_id=r.user_id,
                project_id=r.project_id,
                experiment_id=r.experiment_id,
                meta=r.meta,
                status=GraphQLStatusEnum[Status(r.status).name],
                created_at=r.created_at,
            )
            for r in runs
        ]

    @staticmethod
    def get_run(id: strawberry.ID) -> Run | None:
        metadb = runtime.storage_runtime().metadb
        run = metadb.get_run(run_id=uuid.UUID(id))
        if run:
            return Run(
                id=run.uuid,
                team_id=run.team_id,
                user_id=run.user_id,
                project_id=run.project_id,
                experiment_id=run.experiment_id,
                meta=run.meta,
                status=GraphQLStatusEnum[Status(run.status).name],
                created_at=run.created_at,
            )
        return None

    @staticmethod
    def list_exp_metrics(experiment_id: strawberry.ID) -> list[Metric]:
        metadb = runtime.storage_runtime().metadb
        metrics = metadb.list_metrics_by_experiment_id(experiment_id=experiment_id)
        return [
            Metric(
                id=m.uuid,
                key=m.key,
                value=m.value,
                team_id=m.team_id,
                project_id=m.project_id,
                experiment_id=m.experiment_id,
                run_id=m.run_id,
                created_at=m.created_at,
            )
            for m in metrics
        ]

    @staticmethod
    def total_projects(team_id: strawberry.ID) -> int:
        metadb = runtime.storage_runtime().metadb
        return metadb.count_projects(team_id=team_id)

    @staticmethod
    def total_experiments(team_id: strawberry.ID) -> int:
        metadb = runtime.storage_runtime().metadb
        return metadb.count_experiments(team_id=team_id)

    @staticmethod
    def total_runs(team_id: strawberry.ID) -> int:
        metadb = runtime.storage_runtime().metadb
        return metadb.count_runs(team_id=team_id)

    @staticmethod
    def list_exps_by_timeframe(
        team_id: strawberry.ID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Experiment]:
        metadb = runtime.storage_runtime().metadb
        experiments = metadb.list_exps_by_timeframe(
            team_id=team_id,
            start_time=start_time,
            end_time=end_time,
        )
        return [
            # TODO: use a helper function to convert SQLAlchemy model to GraphQL type
            Experiment(
                id=e.uuid,
                team_id=e.team_id,
                user_id=e.user_id,
                project_id=e.project_id,
                name=e.name,
                description=e.description,
                meta=e.meta,
                params=e.params,
                duration=e.duration,
                status=GraphQLStatusEnum[Status(e.status).name],
                kind=GraphQLExperimentTypeEnum[GraphQLExperimentType(e.kind).name],
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in experiments
        ]


    @staticmethod
    async def list_artifact_repositories(
    ) -> list[ArtifactRepository]:
        """List all repositories in the ORAS registry, optionally filtered by category."""
        registry_url = artifact.get_registry_url()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{registry_url}/v2/_catalog",
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                print(data)
                repositories = data.get("repositories", [])
                print(f"Found repositories: {repositories}")
                return [ArtifactRepository(name=repo) for repo in repositories]
            except httpx.HTTPError as e:
                raise RuntimeError(f"Registry request failed: {e}") from e

    @staticmethod
    async def list_artifact_tags(
        team_id: str, project_id: str, repo_type: str | None = None
    ) -> list[ArtifactTag]:
        """List tags for a repository."""

        arf = artifact.Artifact(team_id=team_id, insecure=True)
        # Append repo_type suffix to project_id if provided (e.g., "project/execution" or "project/checkpoint")
        repo_path = f"{project_id}/{repo_type}" if repo_type else project_id
        return [ArtifactTag(name=tag) for tag in arf.list_versions(repo_path)]

    @staticmethod
    async def get_artifact_content(
        team_id: str, project_id: str, tag: str,  repo_type: str | None = None
    ) -> ArtifactContent:
        """Get artifact content from registry."""
        try:
            # Initialize artifact client
            arf = artifact.Artifact(team_id=team_id, insecure=True)

            # Construct repository path
            repo_path = f"{project_id}/{repo_type}" if repo_type else project_id

            # Pull the artifact - ORAS will manage temp directory
            # Returns absolute paths to files in ORAS temp directory
            # Note: One potential issue is if we download too many large files,
            # it may fill up disk space. For now we assume artifacts are
            # reasonably sized and/or users will manage their registry storage.
            file_paths = arf.pull(repo_name=repo_path, version=tag)

            print(f"Pulled artifact files: {file_paths}")

            if not file_paths:
                raise RuntimeError("No files found in artifact")

            # Read first file content (file_paths now contains absolute paths)
            file_path = file_paths[0]
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Get filename from path
            filename = os.path.basename(file_path)

            # Determine content type based on file extension
            # TODO: for multiple files, this is not right.
            if filename.endswith('.json'):
                content_type = "application/json"
            elif filename.endswith('.txt') or filename.endswith('.log'):
                content_type = "text/plain"
            else:
                content_type = "text/plain"

            return ArtifactContent(
                filename=filename,
                content=content,
                content_type=content_type
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get artifact content: {e}") from e

class GraphQLMutations:
    @staticmethod
    def create_user(input: CreateUserInput) -> User:
        metadb = runtime.storage_runtime().metadb
        user_id = metadb.create_user(
            uuid=uuid.UUID(input.id) if input.id else None,
            username=input.username,
            email=input.email,
            avatar_url=input.avatar_url,
            meta=input.meta,
        )
        user = metadb.get_user(user_id=user_id)
        if user:
            return User(
                id=user.uuid,
                username=user.username,
                email=user.email,
                avatar_url=user.avatar_url,
                meta=user.meta,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        msg = f"Failed to create user with username {input.username}"
        raise RuntimeError(msg)

    @staticmethod
    def update_user(input: UpdateUserInput) -> User:
        metadb = runtime.storage_runtime().metadb
        user_id = uuid.UUID(input.id)

        user = metadb.update_user(user_id=user_id, meta=input.meta)
        if not user:
            msg = f"User with id {input.id} not found"
            raise ValueError(msg)

        return User(
            id=user.uuid,
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url,
            meta=user.meta,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @staticmethod
    def create_team(input: CreateTeamInput) -> Team:
        metadb = runtime.storage_runtime().metadb
        team_id = metadb.create_team(
            uuid=uuid.UUID(input.id) if input.id else None,
            name=input.name,
            description=input.description,
            meta=input.meta,
        )
        team = metadb.get_team(team_id=team_id)
        if team:
            return Team(
                id=team.uuid,
                name=team.name,
                description=team.description,
                meta=team.meta,
                created_at=team.created_at,
                updated_at=team.updated_at,
            )
        msg = f"Failed to create team with name {input.name}"
        raise RuntimeError(msg)

    @staticmethod
    def add_user_to_team(input: AddUserToTeamInput) -> bool:
        metadb = runtime.storage_runtime().metadb
        user_id = uuid.UUID(input.user_id)
        team_id = uuid.UUID(input.team_id)

        # Verify team exists
        team = metadb.get_team(team_id=team_id)
        if not team:
            msg = f"Team with id {input.team_id} not found"
            raise ValueError(msg)

        # Verify user exists
        user = metadb.get_user(user_id=user_id)
        if not user:
            msg = f"User with id {input.user_id} not found"
            raise ValueError(msg)

        # Add user to team (creates TeamMember entry)
        return metadb.add_user_to_team(user_id=user_id, team_id=team_id)

    @staticmethod
    def remove_user_from_team(input: RemoveUserFromTeamInput) -> bool:
        metadb = runtime.storage_runtime().metadb
        user_id = uuid.UUID(input.user_id)
        team_id = uuid.UUID(input.team_id)

        # Verify team exists
        team = metadb.get_team(team_id=team_id)
        if not team:
            msg = f"Team with id {input.team_id} not found"
            raise ValueError(msg)

        # Verify user exists
        user = metadb.get_user(user_id=user_id)
        if not user:
            msg = f"User with id {input.user_id} not found"
            raise ValueError(msg)

        # Remove user from team (deletes TeamMember entry)
        return metadb.remove_user_from_team(user_id=user_id, team_id=team_id)
