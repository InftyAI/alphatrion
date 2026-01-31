import asyncio
import contextlib
import signal
import uuid

from pydantic import BaseModel, Field

from alphatrion.experiment import base as experiment
from alphatrion.runtime.runtime import global_runtime
from alphatrion.utils import context


class ProjectConfig(BaseModel):
    """Configuration for a Project."""

    max_execution_seconds: int = Field(
        default=-1,
        description="Maximum execution seconds for the project. \
            Once exceeded, the project and all its experiments will be cancelled. \
            Default is -1 (no limit).",
    )


class Project:
    """
    Project represents a collection of experiments. Only one project can be active
    at a time in the runtime.
    """

    __slots__ = (
        "_id",
        "_runtime",
        "_experiments",
        "_config",
        "_context",
        "_signal_task",
        "_stopped",
    )

    def __init__(self, config: ProjectConfig | None = None):
        self._runtime = global_runtime()
        # All experiments in this project,
        # key is experiment_id, value is Experiment instance.
        self._experiments: dict[int, experiment.Experiment] = {}
        self._config = config or ProjectConfig()
        self._runtime.current_proj = self

        self._context = context.Context(
            cancel_func=self._stop,
            timeout=self._config.max_execution_seconds
            if self._config.max_execution_seconds > 0
            else None,
        )
        self._signal_task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    @property
    def id(self):
        return self._id

    @classmethod
    def setup(
        cls,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        config: ProjectConfig | None = None,
    ) -> "Project":
        """
        Setup the experiment. If the name already exists in the same project,
        it will refer to the existing experiment instead of creating a new one.
        """

        proj = Project(config)
        proj_obj = proj._get_by_name(name=name)

        # If project with the same name exists in the project, use it.
        if proj_obj:
            proj._id = proj_obj.uuid
        else:
            proj._create(
                name=name,
                description=description,
                meta=meta,
            )

        return proj

    def _start_signal_handlers(self):
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._on_signal)

        return asyncio.create_task(self._wait_for_stop())

    def _on_signal(self):
        self._stopped.set()

    async def _wait_for_stop(self):
        await self._stopped.wait()
        self.done()

    async def __aenter__(self):
        if self._id is None:
            raise RuntimeError("Project is not set. Did you call start()?")

        project = self._get()
        if project is None:
            raise RuntimeError(f"Project {self._id} not found in the database.")

        self._signal_task = self._start_signal_handlers()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.done()

        if self._signal_task:
            self._signal_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await self._signal_task

    def get_experiment(self, id: int) -> experiment.Experiment | None:
        return self._experiments.get(id)

    # done() is safe to call multiple times.
    def done(self):
        self._cancel()

    def _cancel(self):
        return self._context.cancel()

    def _stop(self):
        for t in list(self._experiments.values()):
            t.done()
        self._experiments = dict()
        # Set to None at the end of the project because
        # it will be used in experiment.done().
        self._runtime.current_proj = None

    def register_experiment(self, id: uuid.UUID, instance: experiment.Experiment):
        self._experiments[id] = instance

    def unregister_experiment(self, id: uuid.UUID):
        self._experiments.pop(id, None)

    def _create(
        self,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
    ):
        """
        :param name: the name of the project.
        :param description: the description of the project
        :param meta: the metadata of the project

        :return: the project ID
        """

        self._id = self._runtime._metadb.create_project(
            name=name,
            description=description,
            team_id=self._runtime._team_id,
            user_id=self._runtime._user_id,
            meta=meta,
        )
        return self._id

    def _get(self):
        return self._runtime._metadb.get_project(project_id=self._id)

    def _get_by_name(self, name: str):
        return self._runtime._metadb.get_proj_by_name(
            name=name, team_id=self._runtime._team_id
        )

    def delete(self):
        exp = self._get()
        if exp is None:
            return

        self._runtime._metadb.delete_project(project_id=self._id)
        # TODO: Should we make this optional as a parameter?
        tags = self._runtime._artifact.list_versions(repo_name=str(self._id))
        self._runtime._artifact.delete(repo_name=str(self._id), versions=tags)
