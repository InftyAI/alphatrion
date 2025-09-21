import contextvars
from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

from alphatrion.metadata.sql_models import COMPLETED_STATUS, TrialStatus
from alphatrion.runtime.runtime import global_runtime

# Used in record/record.py to log params/metrics
current_trial_id = contextvars.ContextVar("current_trial_id", default=None)


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


class TrialConfig(BaseModel):
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


class Trial:
    __slots__ = (
        "_id",
        "_exp_id",
        "_config",
        "_runtime",
        "_token",
        "_step",
    )

    def __init__(self, exp_id: int, config: TrialConfig | None = None):
        self._exp_id = exp_id
        self._config = config or TrialConfig()
        self._runtime = global_runtime()
        # step is used to track the round, e.g. the step in metric logging.
        self._step = 0

    def _start(
        self,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
    ) -> int:
        self._id = self._runtime._metadb.create_trial(
            exp_id=self._exp_id,
            description=description,
            meta=meta,
            params=params,
            status=TrialStatus.RUNNING,
        )

        self._token = current_trial_id.set(self._id)
        return self._id

    @property
    def id(self):
        return self._id

    # finish function should be called manually as a pair of start
    def finish(self, status: TrialStatus = TrialStatus.FINISHED):
        trial = self._runtime._metadb.get_trial(trial_id=self._id)
        if trial is not None and trial.status not in COMPLETED_STATUS:
            duration = (
                datetime.now(UTC) - trial.created_at.replace(tzinfo=UTC)
            ).total_seconds()
            self._runtime._metadb.update_trial(
                trial_id=self._id, status=status, duration=duration
            )

        # recover the context var
        current_trial_id.reset(self._token)

    def _get(self):
        return self._runtime._metadb.get_trial(trial_id=self._id)

    def increment_step(self) -> int:
        self._step += 1
        return self._step
