import contextvars
import enum
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

from alphatrion.metadata.sql_models import FINISHED_STATUS, Status
from alphatrion.run.run import Run
from alphatrion.runtime.runtime import global_runtime
from alphatrion.utils import context

# Used in log/log.py to log params/metrics
current_trial_id = contextvars.ContextVar("current_trial_id", default=None)


class CheckpointConfig(BaseModel):
    """Configuration for a checkpoint."""

    enabled: bool = Field(
        default=False,
        description="Whether to enable checkpointing. \
            Default is False.",
    )
    # save_every_n_seconds: int | None = Field(
    #     default=None,
    #     description="Interval in seconds to save checkpoints. \
    #         Default is None.",
    # )
    # TODO: implement save_every_n_runs
    save_every_n_runs: int = Field(
        default=-1,
        description="Interval in runs to save checkpoints. \
            Default is -1 (unlimited).",
    )
    save_on_best: bool = Field(
        default=False,
        description="Once a best result is found, it will be saved. \
            The metric to monitor is specified by monitor_metric. Default is False. \
            Can be enabled together with save_every_n_steps/save_every_n_seconds.",
    )
    path: str = Field(
        default="checkpoints",
        description="The path to save checkpoints. Default is 'checkpoints'.",
    )


class MonitorMode(enum.Enum):
    MAX = "max"
    MIN = "min"


class TrialConfig(BaseModel):
    """Configuration for a Trial."""

    max_execution_seconds: int = Field(
        default=-1,
        description="Maximum execution seconds for the trial. \
        Trial timeout will override experiment timeout if both are set. \
        Default is -1 (no limit).",
    )
    early_stopping_runs: int = Field(
        default=-1,
        description="Number of runs with no improvement \
        after which the trial will be stopped. Default is -1 (no early stopping). \
        Count each time when calling log_metrics with the monitored metric.",
    )
    max_runs_per_trial: int = Field(
        default=-1,
        description="Maximum number of runs for each trial. \
        Default is -1 (no limit). Count by the finished runs.",
    )
    monitor_metric: str | None = Field(
        default=None,
        description="The metric to monitor together with other configurations  \
            like early_stopping_runs and save_on_best. \
            Required if save_on_best is true or early_stopping_runs > 0 \
            or target_metric_value is not None.",
    )
    monitor_mode: MonitorMode = Field(
        default=MonitorMode.MAX,
        description="The mode for monitoring the metric. Can be 'max' or 'min'. \
            Default is 'max'.",
    )
    target_metric_value: float | None = Field(
        default=None,
        description="If specified, the trial will stop when \
            the monitored metric reaches this target value. \
            If monitor_mode is 'max', the trial will stop when \
            the metric >= target_metric_value. If monitor_mode is 'min', \
            the trial will stop when the metric <= target_metric_value. \
            Default is None (no target).",
    )
    checkpoint: CheckpointConfig = Field(
        default=CheckpointConfig(),
        description="Configuration for checkpointing.",
    )

    @model_validator(mode="after")
    def metric_must_be_valid(self):
        if self.checkpoint.save_on_best and not self.monitor_metric:
            raise ValueError(
                "monitor_metric must be specified \
                when checkpoint.save_on_best=True"
            )
        if self.early_stopping_runs > 0 and not self.monitor_metric:
            raise ValueError(
                "monitor_metric must be specified \
                when early_stopping_runs>0"
            )
        if self.target_metric_value is not None and not self.monitor_metric:
            raise ValueError(
                "monitor_metric must be specified \
                when target_metric_value is set"
            )
        return self


class Trial:
    __slots__ = (
        "_id",
        "_exp_id",
        "_config",
        "_runtime",
        # step is used to track the round, e.g. the step in metric logging.
        "_step",
        "_context",
        "_token",
        # _meta stores the runtime meta information of the trial.
        # * best_metrics: dict of best metric values, used for checkpointing and
        #   early stopping. When the workload(e.g. Pod) restarts, the meta info
        #   will be lost and start from scratch. Then once some features like
        #   early_stopping_runs is enabled, it may lead to unexpected behaviors like
        #   never stopping because the counter is reset everytime restarted.
        #   To avoid this, you can set the restart times for the workload.
        "_meta",
        # key is run_id, value is Run instance
        "_runs",
        # Only work when early_stopping_runs > 0
        "_early_stopping_counter",
        # Only work when max_runs_per_trial > 0
        "_total_runs_counter",
        # Whether the trial is ended with error.
        "_err",
    )

    def __init__(self, exp_id: int, config: TrialConfig | None = None):
        self._exp_id = exp_id
        self._config = config or TrialConfig()
        self._runtime = global_runtime()
        self._step = 0
        self._construct_meta()
        self._runs = dict[uuid.UUID, Run]()
        self._early_stopping_counter = 0
        self._total_runs_counter = 0
        self._err = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.done()
        if self._token:
            current_trial_id.reset(self._token)

    @property
    def id(self) -> uuid.UUID:
        return self._id

    def _construct_meta(self):
        self._meta = dict()

        # TODO: if restart from existing trial, load the best_metrics from database.
        if self._config.monitor_mode == MonitorMode.MAX:
            self._meta["best_metrics"] = {self._config.monitor_metric: float("-inf")}
        elif self._config.monitor_mode == MonitorMode.MIN:
            self._meta["best_metrics"] = {self._config.monitor_metric: float("inf")}
        else:
            raise ValueError(f"Invalid monitor_mode: {self._config.monitor_mode}")

    def config(self) -> TrialConfig:
        return self._config

    def should_checkpoint_on_best(self, metric_key: str, metric_value: float) -> bool:
        is_best_metric = self._save_if_best_metric(metric_key, metric_value)
        return (
            self._config.checkpoint.enabled
            and self._config.checkpoint.save_on_best
            and is_best_metric
        )

    def _save_if_best_metric(self, metric_key: str, metric_value: float) -> bool:
        """Save the metric if it is the best so far.
        Returns True if the metric is the best so far, False otherwise.
        """
        if metric_key != self._config.monitor_metric:
            return False

        best_value = self._meta["best_metrics"][metric_key]

        if self._config.monitor_mode == MonitorMode.MAX:
            if metric_value > best_value:
                self._meta["best_metrics"][metric_key] = metric_value
                return True
        elif self._config.monitor_mode == MonitorMode.MIN:
            if metric_value < best_value:
                self._meta["best_metrics"][metric_key] = metric_value
                return True
        else:
            raise ValueError(f"Invalid monitor_mode: {self._config.monitor_mode}")

        return False

    def should_stop_on_target_metric(
        self, metric_key: str, metric_value: float
    ) -> bool:
        """Check if the metric meets the target metric value."""
        if (
            self._config.target_metric_value is None
            or metric_key != self._config.monitor_metric
        ):
            return False

        target_value = self._config.target_metric_value

        if self._config.monitor_mode == MonitorMode.MAX:
            return metric_value >= target_value
        elif self._config.monitor_mode == MonitorMode.MIN:
            return metric_value <= target_value
        else:
            raise ValueError(f"Invalid monitor_mode: {self._config.monitor_mode}")

    def should_early_stop(self, metric_key: str, metric_value: float) -> bool:
        if (
            self._config.early_stopping_runs <= 0
            or metric_key != self._config.monitor_metric
        ):
            return False

        best_value = self._meta["best_metrics"][metric_key]

        if self._config.monitor_mode == MonitorMode.MAX:
            if metric_value < best_value:
                self._early_stopping_counter += 1
            else:
                self._early_stopping_counter = 0
        elif self._config.monitor_mode == MonitorMode.MIN:
            if metric_value > best_value:
                self._early_stopping_counter += 1
            else:
                self._early_stopping_counter = 0
        else:
            raise ValueError(f"Invalid monitor_mode: {self._config.monitor_mode}")

        return self._early_stopping_counter >= self._config.early_stopping_runs

    def _timeout(self) -> int | None:
        timeout = self._config.max_execution_seconds
        if timeout is None or timeout < 0:
            return None

        obj = self._get_obj()
        if obj is None:
            return timeout

        elapsed = (
            datetime.now(UTC) - obj.created_at.replace(tzinfo=UTC)
        ).total_seconds()
        timeout -= int(elapsed)

        return timeout

    # Make sure you have termination condition, either by timeout or by calling cancel()
    # Before we have logic like once all the tasks are done, we'll call the cancel()
    # automatically, however, this is unpredictable because some tasks may be waiting
    # for external events, so we leave it to the user to decide when to stop the trial.
    async def wait(self):
        await self._context.wait()

    def is_done(self) -> bool:
        return self._context.cancelled()

    # If the name is same in the same experiment, it will refer to the existing trial.
    def _start(
        self,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
    ):
        trial_obj = self._runtime._metadb.get_trial_by_name(
            trial_name=name, experiment_id=self._exp_id
        )
        # FIXME: what if the existing trial is completed, will lead to confusion?
        if trial_obj:
            self._id = trial_obj.uuid
        else:
            self._id = self._runtime._metadb.create_trial(
                project_id=self._runtime._project_id,
                experiment_id=self._exp_id,
                name=name,
                description=description,
                meta=meta,
                params=params,
                status=Status.RUNNING,
            )

        self._context = context.Context(
            cancel_func=self._stop,
            timeout=self._timeout(),
        )

        # We don't reset the trial id context var here, because
        # each trial runs in its own context.
        self._token = current_trial_id.set(self._id)

    # done function should be called manually as a pair of start
    # FIXME: watch for system signals to cancel the trial gracefully,
    # or it could lead to trial not being marked as completed.
    def done(self):
        self._cancel()

    def done_with_err(self):
        self._err = True
        self._cancel()

    def _cancel(self):
        self._context.cancel()

    def _stop(self):
        trial = self._runtime._metadb.get_trial(trial_id=self._id)
        if trial is not None and trial.status not in FINISHED_STATUS:
            duration = (
                datetime.now(UTC) - trial.created_at.replace(tzinfo=UTC)
            ).total_seconds()

            status = Status.COMPLETED
            if self._err:
                status = Status.FAILED

            self._runtime._metadb.update_trial(
                trial_id=self._id, status=status, duration=duration
            )

        self._runtime.current_exp.unregister_trial(self._id)
        for run in self._runs.values():
            run.cancel()
        self._runs.clear()

    def _get_obj(self):
        return self._runtime.metadb.get_trial(trial_id=self._id)

    def increment_step(self) -> int:
        self._step += 1
        return self._step

    def start_run(self, call_func: callable) -> Run:
        """Start a new run for the trial.
        :param call_func: a callable function that returns a coroutine.
                          It must be a async and lambda function.
        :return: the Run instance."""

        run = Run(trial_id=self._id)
        run.start(call_func)
        self._runs[run.id] = run

        run.add_done_callback(
            lambda t: (
                setattr(self, "_total_runs_counter", self._total_runs_counter + 1),
                self._post_run(run),
            )
        )
        return run

    def _post_run(self, run: Run):
        self._runs.pop(run.id, None)
        run.done()

        if (
            self._config.max_runs_per_trial > 0
            and self._total_runs_counter >= self._config.max_runs_per_trial
        ):
            self.done()
