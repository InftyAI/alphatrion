import os
import uuid
from datetime import datetime

import httpx
import strawberry

from alphatrion import envs
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
    DailyTokenUsage,
    Experiment,
    GraphQLExperimentType,
    GraphQLExperimentTypeEnum,
    GraphQLStatusEnum,
    Label,
    Metric,
    RemoveUserFromTeamInput,
    Run,
    Span,
    Team,
    TraceEvent,
    TraceLink,
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
    def list_labels_by_exp_id(experiment_id: strawberry.ID) -> list[Label]:
        metadb = runtime.storage_runtime().metadb
        labels = metadb.list_labels_by_exp_id(experiment_id=experiment_id)
        return [
            Label(
                name=label.label_name,
                value=label.label_value,
            )
            for label in labels
        ]

    @staticmethod
    def list_experiments(
        team_id: strawberry.ID,
        page: int = 0,
        page_size: int = 20,
        order_by: str = "created_at",
        order_desc: bool = True,
        label_name: str | None = None,
        label_value: str | None = None,
    ) -> list[Experiment]:
        metadb = runtime.storage_runtime().metadb
        if label_name:
            exps = metadb.list_exps_by_label(
                team_id=uuid.UUID(team_id),
                label_name=label_name,
                label_value=label_value,
                page=page,
                page_size=page_size,
                order_by=order_by,
                order_desc=order_desc,
            )
        else:
            exps = metadb.list_exps_by_team_id(
                team_id=uuid.UUID(team_id),
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
                experiment_id=r.experiment_id,
                meta=r.meta,
                status=GraphQLStatusEnum[Status(r.status).name],
                duration=r.duration,
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
                experiment_id=run.experiment_id,
                meta=run.meta,
                status=GraphQLStatusEnum[Status(run.status).name],
                duration=run.duration,
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
                experiment_id=m.experiment_id,
                run_id=m.run_id,
                created_at=m.created_at,
            )
            for m in metrics
        ]

    @staticmethod
    def list_run_metrics(run_id: strawberry.ID) -> list[Metric]:
        metadb = runtime.storage_runtime().metadb
        metrics = metadb.list_metrics_by_run_id(run_id=run_id)
        return [
            Metric(
                id=m.uuid,
                key=m.key,
                value=m.value,
                team_id=m.team_id,
                experiment_id=m.experiment_id,
                run_id=m.run_id,
                created_at=m.created_at,
            )
            for m in metrics
        ]

    @staticmethod
    def total_experiments(team_id: strawberry.ID) -> int:
        metadb = runtime.storage_runtime().metadb
        return metadb.count_experiments(team_id=team_id)

    @staticmethod
    def total_runs(team_id: strawberry.ID) -> int:
        metadb = runtime.storage_runtime().metadb
        return metadb.count_runs(team_id=team_id)

    @staticmethod
    def aggregate_team_tokens(team_id: strawberry.ID) -> dict[str, int]:
        from alphatrion import envs

        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}

        trace_store = runtime.storage_runtime().tracestore
        result = trace_store.get_llm_spans_by_team_id(team_id=team_id)
        # get_llm_spans_by_team_id returns a list with one dict
        if result and len(result) > 0:
            return result[0]
        return {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}

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
    async def list_artifact_repositories() -> list[ArtifactRepository]:
        """List all repositories in the ORAS registry."""

        registry_url = artifact.get_registry_url()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{registry_url}/v2/_catalog",
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                repositories = data.get("repositories", [])
                return [ArtifactRepository(name=repo) for repo in repositories]
            except httpx.HTTPError as e:
                raise RuntimeError(f"Registry request failed: {e}") from e

    @staticmethod
    async def list_artifact_tags(
        team_id: str,
        repo_name: str,
    ) -> list[ArtifactTag]:
        """List tags for a repository."""

        arf = artifact.Artifact(team_id=team_id, insecure=True)
        return [ArtifactTag(name=tag) for tag in arf.list_versions(repo_name)]

    @staticmethod
    async def get_artifact_content(
        team_id: str, tag: str, repo_name: str | None = None
    ) -> ArtifactContent:
        """Get artifact content from registry."""
        try:
            # Initialize artifact client
            arf = artifact.Artifact(team_id=team_id, insecure=True)

            # Pull the artifact - ORAS will manage temp directory
            # Returns absolute paths to files in ORAS temp directory
            # Note: One potential issue is if we download too many large files,
            # it may fill up disk space. For now we assume artifacts are
            # reasonably sized and/or users will manage their registry storage.
            file_paths = arf.pull(repo_name=repo_name, version=tag)

            if not file_paths:
                raise RuntimeError("No files found in artifact")

            # Read first file content (file_paths now contains absolute paths)
            file_path = file_paths[0]
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Get filename from path
            filename = os.path.basename(file_path)

            # Determine content type based on file extension
            # TODO: for multiple files, this is not right.
            if filename.endswith(".json"):
                content_type = "application/json"
            elif filename.endswith(".txt") or filename.endswith(".log"):
                content_type = "text/plain"
            else:
                content_type = "text/plain"

            return ArtifactContent(
                filename=filename, content=content, content_type=content_type
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get artifact content: {e}") from e

    @staticmethod
    def aggregate_run_tokens(run_id: strawberry.ID) -> dict[str, int]:
        """Aggregate token usage from all traces for a run."""
        from alphatrion import envs

        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}

        try:
            trace_store = runtime.storage_runtime().tracestore
            spans = trace_store.get_llm_spans_by_run_id(run_id)
            # Don't close - it's a shared singleton connection

            total_tokens = 0
            input_tokens = 0
            output_tokens = 0

            for span in spans:
                span_attrs = span.get("SpanAttributes", {})

                # Aggregate tokens from LLM spans
                if "llm.usage.total_tokens" in span_attrs:
                    total_tokens += int(span_attrs["llm.usage.total_tokens"])
                if "gen_ai.usage.input_tokens" in span_attrs:
                    input_tokens += int(span_attrs["gen_ai.usage.input_tokens"])
                if "gen_ai.usage.output_tokens" in span_attrs:
                    output_tokens += int(span_attrs["gen_ai.usage.output_tokens"])

            return {
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        except Exception as e:
            import logging

            logging.error(
                f"Failed to aggregate tokens for run {run_id}: {e}", exc_info=True
            )
            return {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}

    @staticmethod
    def aggregate_experiment_tokens(experiment_id: strawberry.ID) -> dict[str, int]:
        """Aggregate token usage from all spans in an experiment."""

        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}

        try:
            trace_store = runtime.storage_runtime().tracestore
            # Get all LLM spans for this experiment in a single query
            spans = trace_store.get_llm_spans_by_exp_id(experiment_id)
            # Don't close - it's a shared singleton connection

            total_tokens = 0
            input_tokens = 0
            output_tokens = 0

            for span in spans:
                span_attrs = span.get("SpanAttributes", {})

                # Aggregate tokens from LLM spans
                if "llm.usage.total_tokens" in span_attrs:
                    total_tokens += int(span_attrs["llm.usage.total_tokens"])
                if "gen_ai.usage.input_tokens" in span_attrs:
                    input_tokens += int(span_attrs["gen_ai.usage.input_tokens"])
                if "gen_ai.usage.output_tokens" in span_attrs:
                    output_tokens += int(span_attrs["gen_ai.usage.output_tokens"])

            return {
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        except Exception as e:
            import logging

            logging.error(
                f"Failed to aggregate tokens for experiment {experiment_id}: {e}"
            )
            return {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}

    @staticmethod
    def list_spans(run_id: strawberry.ID) -> list[Span]:
        """List all spans for a specific run."""
        from alphatrion import envs

        # Check if tracing is enabled
        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return []

        try:
            trace_store = runtime.storage_runtime().tracestore

            # Get traces from ClickHouse
            raw_spans = trace_store.get_spans_by_run_id(uuid.UUID(run_id))
            # Don't close - it's a shared singleton connection

            # Convert to GraphQL Span objects
            spans = []
            for t in raw_spans:
                # Convert events from ClickHouse flat arrays
                events = []
                event_timestamps = t.get("EventTimestamps", [])
                event_names = t.get("EventNames", [])
                event_attrs = t.get("EventAttributes", [])
                for i in range(len(event_names)):
                    events.append(
                        TraceEvent(
                            timestamp=event_timestamps[i]
                            if i < len(event_timestamps)
                            else datetime.now(),
                            name=event_names[i],
                            attributes=event_attrs[i] if i < len(event_attrs) else {},
                        )
                    )

                # Convert links from ClickHouse flat arrays
                links = []
                link_trace_ids = t.get("LinkTraceIds", [])
                link_span_ids = t.get("LinkSpanIds", [])
                link_attrs = t.get("LinkAttributes", [])
                for i in range(len(link_trace_ids)):
                    links.append(
                        TraceLink(
                            trace_id=link_trace_ids[i],
                            span_id=link_span_ids[i] if i < len(link_span_ids) else "",
                            attributes=link_attrs[i] if i < len(link_attrs) else {},
                        )
                    )

                spans.append(
                    Span(
                        timestamp=t["Timestamp"],
                        trace_id=t["TraceId"],
                        span_id=t["SpanId"],
                        parent_span_id=t["ParentSpanId"],
                        span_name=t["SpanName"],
                        span_kind=t["SpanKind"],
                        semantic_kind=t["SemanticKind"],
                        service_name=t["ServiceName"],
                        duration=t["Duration"],
                        status_code=t["StatusCode"],
                        status_message=t["StatusMessage"],
                        team_id=t["TeamId"],
                        run_id=t["RunId"],
                        experiment_id=t["ExperimentId"],
                        span_attributes=t["SpanAttributes"],
                        resource_attributes=t["ResourceAttributes"],
                        events=events,
                        links=links,
                    )
                )

            return spans
        except Exception as e:
            # Log error and return empty list - don't fail the GraphQL query
            print(f"Failed to fetch traces: {e}")
            return []

    # Alias for list_spans
    list_traces = list_spans

    @staticmethod
    def get_daily_token_usage(
        team_id: strawberry.ID, days: int = 7
    ) -> list[DailyTokenUsage]:
        """Get daily token usage from LLM calls for a team."""
        from alphatrion import envs

        # Check if tracing is enabled
        if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
            return []

        try:
            trace_store = runtime.storage_runtime().tracestore
            daily_usage = trace_store.get_daily_token_usage(
                team_id=uuid.UUID(team_id), days=days
            )
            # Don't close - it's a shared singleton connection

            # Convert to GraphQL DailyTokenUsage objects
            return [
                DailyTokenUsage(
                    date=item["date"],
                    total_tokens=item["total_tokens"],
                    input_tokens=item["input_tokens"],
                    output_tokens=item["output_tokens"],
                )
                for item in daily_usage
            ]
        except Exception as e:
            # Log error and return empty list - don't fail the GraphQL query
            print(f"Failed to fetch daily token usage: {e}")
            return []


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
