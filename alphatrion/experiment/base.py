import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

from alphatrion.artifact.artifact import Artifact
from alphatrion.metadata.sql_models import COMPLETED_STATUS, ExperimentStatus
from alphatrion.runtime.runtime import Runtime


class CheckpointConfig(BaseModel):
    """Configuration for a checkpoint."""

    enabled: bool = Field(
        default=True,
        description="Whether to enable checkpointing. \
            Default is True. One exception is CraftExperiment, \
            which doesn't enable checkpoint by default.",
    )
    save_every_n_seconds: int = Field(
        default=300,
        description="Interval in seconds to save checkpoints. \
            Default is 300 seconds.",
    )
    save_every_n_steps: int = Field(
        default=0,
        description="Interval in steps to save checkpoints. \
            Default is 0 (disabled).",
    )
    save_best_only: bool = Field(
        default=True,
        description="Once a best result is found, it will be saved. Default is True. \
            Can be enabled together with save_every_n_steps/save_every_n_seconds.",
    )
    monitor_metric: str = Field(
        default=None,
        description="The metric to monitor for saving the best checkpoint. \
            Required if save_best_only is True.",
    )
    monitor_mode: str = Field(
        default="max",
        description="The mode for monitoring the metric. Can be 'max' or 'min'. \
            Default is 'max'.",
    )

    @field_validator("monitor_metric")
    def metric_must_be_valid(cls, v, info):
        save_best_only = info.data.get("save_best_only")
        if save_best_only and v is None:
            raise ValueError("metric must be specified when save_best_only=True")
        return v


class ExperimentConfig(BaseModel):
    """Configuration for an experiment."""

    max_duration_seconds: int = Field(
        default=86400,
        description="Maximum duration in seconds for the experiment. \
        Default is 86400 seconds (1 day).",
    )
    max_retries: int = Field(
        default=0,
        description="Maximum number of retries for the experiment. \
            Default is 0 (no retries).",
    )
    checkpoint: CheckpointConfig = Field(
        default=CheckpointConfig(),
        description="Configuration for checkpointing.",
    )


class Experiment:
    """Base Experiment class."""

    def __init__(self, runtime: Runtime, config: ExperimentConfig | None = None):
        self._runtime = runtime
        self._artifact = Artifact(runtime)
        self._config = config or ExperimentConfig()

        self._steps = 0
        self._best_metric_value = None
        # Start time of the experiment. Set when experiment is started,
        # reset to None when experiment is stopped.
        self._start_at = None
        # Running Experiment ID that is stored in the metadata database.
        # Set when experiment is created, reset to None when experiment is stopped.
        self._exp_id = None

    @classmethod
    def run(
        cls,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        meta: dict | None = None,
        labels: dict | None = None,
    ):
        runtime = Runtime(project_id=project_id)
        exp = cls(runtime=runtime)
        return RunContext(
            exp, name=name, description=description, meta=meta, labels=labels
        )

    def create(
        self,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        labels: dict | None = None,
    ):
        """
        Create a new experiment in the metadata store.
        Returns the experiment ID.
        """

        self._exp_id = self._runtime._metadb.create_exp(
            name=name,
            description=description,
            project_id=self._runtime._project_id,
            meta=meta,
            labels=labels,
        )

        return self._exp_id

    def get(self, exp_id: int):
        return self._runtime._metadb.get_exp(exp_id=exp_id)

    def list(self, page: int = 0, page_size: int = 10):
        return self._runtime._metadb.list_exps(
            project_id=self._runtime._project_id, page=page, page_size=page_size
        )

    # TODO: delete related artifacts too. But for google artifact registry,
    # it seems not supported to delete a tag only.
    # See issue: https://github.com/InftyAI/alphatrion/issues/14
    def delete(self, exp_id: int):
        self._runtime._metadb.delete_exp(exp_id=exp_id)

    # Please provide all the labels to update, or it will overwrite the existing labels.
    def update_labels(self, exp_id: int, labels: dict):
        self._runtime._metadb.update_exp(exp_id=exp_id, labels=labels)

    def start(
        self,
        name: str | None = None,
        description: str | None = None,
        meta: dict | None = None,
        labels: dict | None = None,
    ) -> int:
        """
        Start a new experiment. If name is not provided, a UUID will be generated.
        Returns the experiment ID.
        """

        if name is None:
            name = f"{uuid.uuid4()}"

        exp_id = self.create(
            name=name,
            description=description,
            meta=meta,
            labels=labels,
        )
        self._runtime._metadb.update_exp(exp_id=exp_id, status=ExperimentStatus.RUNNING)
        self._start_at = datetime.now(UTC)
        return exp_id

    def stop(self, exp_id: int, status: ExperimentStatus = ExperimentStatus.FINISHED):
        exp = self._runtime._metadb.get_exp(exp_id=exp_id)
        if exp is not None and exp.status not in COMPLETED_STATUS:
            duration = (datetime.now() - exp.created_at).total_seconds()
            self._runtime._metadb.update_exp(
                exp_id=exp_id, status=status, duration=duration
            )

    def status(self, exp_id: int) -> ExperimentStatus:
        exp = self._runtime._metadb.get_exp(exp_id=exp_id)
        return exp.status

    def reset(self):
        self._steps = 0
        self._start_at = None
        self._best_metric_value = None
        self._exp_id = None

    def running_experiment_id(self) -> int | None:
        return self._exp_id

    # running time in seconds since the experiment is started.
    def running_time(self) -> int:
        if self._start_at is None:
            return 0
        return int((datetime.now(UTC) - self._start_at).total_seconds())

    # def save_checkpoint(
    #     self,
    #     exp_id: int,
    #     files: list[str] | None = None,
    #     folder: str | None = None,
    #     version: str = "latest",
    # ):
    #     exp = self._runtime._metadb.get_exp(exp_id=exp_id)
    #     self._artifact.push(
    #         experiment_name=exp.name, files=files, folder=folder, version=version
    #     )


class RunContext:
    """A context manager for running experiments."""

    def __init__(
        self,
        experiment: Experiment,
        name: str | None = None,
        description: str | None = None,
        meta: dict | None = None,
        labels: dict | None = None,
    ):
        self._experiment = experiment
        self._exp_name = name
        self._description = description
        self._meta = meta
        self._labels = labels

    def __enter__(self):
        self._experiment.start(
            name=self._exp_name,
            description=self._description,
            meta=self._meta,
            labels=self._labels,
        )
        return self._experiment

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._experiment.stop(self._experiment._exp_id)
        self._experiment.reset()
