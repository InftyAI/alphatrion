import contextvars
import os
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

from alphatrion.metadata.sql_models import COMPLETED_STATUS, TrialStatus
from alphatrion.run.run import Run
from alphatrion.runtime.runtime import global_runtime
from alphatrion.utils.context import Context

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
    # save_every_n_steps: int | None = Field(
    #     default=None,
    #     description="Interval in steps to save checkpoints. \
    #         Default is None.",
    # )
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


class TrialConfig(BaseModel):
    """Configuration for an experiment."""

    max_runtime_seconds: int = Field(
        default=-1,
        description="Maximum runtime seconds for the trial. \
        Trial timeout will override experiment timeout if both are set. \
        Default is -1 (no limit).",
    )
    early_stopping_runs: int = Field(
        default=-1,
        description="Number of runs with no improvement \
        after which experiment will be stopped. Default is -1 (no early stopping). \
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
            Required if save_on_best is true or early_stopping_runs > 0.",
    )
    monitor_mode: str = Field(
        default="max",
        description="The mode for monitoring the metric. Can be 'max' or 'min'. \
            Default is 'max'.",
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
        "_running_tasks",
        # Only work when early_stopping_runs > 0
        "_early_stopping_counter",
        # Only work when max_runs_per_trial > 0
        "_total_runs_counter",
    )

    def __init__(self, exp_id: int, config: TrialConfig | None = None):
        self._exp_id = exp_id
        self._config = config or TrialConfig()
        self._runtime = global_runtime()
        self._step = 0
        self._context = Context(
            cancel_func=self._stop,
            timeout=self._timeout(),
        )
        self._construct_meta()
        self._runs = dict()
        self._running_tasks = dict()
        self._early_stopping_counter = 0
        self._total_runs_counter = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.cancel()
        if self._token:
            current_trial_id.reset(self._token)

    @property
    def id(self) -> uuid.UUID:
        return self._id

    def _construct_meta(self):
        self._meta = dict()

        if self._config.monitor_mode == "max":
            self._meta["best_metrics"] = {self._config.monitor_metric: float("-inf")}
        elif self._config.monitor_mode == "min":
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

        if self._config.monitor_mode == "max":
            if metric_value > best_value:
                self._meta["best_metrics"][metric_key] = metric_value
                return True
        elif self._config.monitor_mode == "min":
            if metric_value < best_value:
                self._meta["best_metrics"][metric_key] = metric_value
                return True
        else:
            raise ValueError(f"Invalid monitor_mode: {self._config.monitor_mode}")

        return False

    def should_early_stop(self, metric_key: str, metric_value: float) -> bool:
        if (
            self._config.early_stopping_runs <= 0
            or metric_key != self._config.monitor_metric
        ):
            return False

        best_value = self._meta["best_metrics"][metric_key]

        if self._config.monitor_mode == "max":
            if metric_value < best_value:
                self._early_stopping_counter += 1
            else:
                self._early_stopping_counter = 0
        elif self._config.monitor_mode == "min":
            if metric_value > best_value:
                self._early_stopping_counter += 1
            else:
                self._early_stopping_counter = 0
        else:
            raise ValueError(f"Invalid monitor_mode: {self._config.monitor_mode}")

        return self._early_stopping_counter >= self._config.early_stopping_runs

    def _timeout(self) -> int | None:
        timeout = self._config.max_runtime_seconds
        if timeout < 0:
            return None

        # Adjust timeout based on the trial start time from environment variable,
        # this is useful when running in cloud env when the trial process may be
        # restarted.
        start_time = os.environ.get("ALPHATRION_TRIAL_START_TIME", None)
        if start_time is not None:
            elapsed = (
                datetime.now(UTC)
                - datetime.fromisoformat(start_time).replace(tzinfo=UTC)
            ).total_seconds()
            timeout -= int(elapsed)
        return timeout

    # Make sure you have termination condition, either by timeout or by calling cancel()
    # Before we have logic like once all the tasks are done, we'll call the cancel()
    # automatically, however, this is unpredictable because some tasks may be waiting
    # for external events, so we leave it to the user to decide when to stop the trial.
    async def wait(self):
        await self._context.wait()

    def cancelled(self) -> bool:
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
            trial_name=name, exp_id=self._exp_id
        )
        # FIXME: what if the existing trial is finished, will lead to confusion?
        if trial_obj:
            self._id = trial_obj.uuid
        else:
            self._id = self._runtime._metadb.create_trial(
                project_id=self._runtime._project_id,
                exp_id=self._exp_id,
                name=name,
                description=description,
                meta=meta,
                params=params,
                status=TrialStatus.RUNNING,
            )

        # We don't reset the trial id context var here, because
        # each trial runs in its own context.
        self._token = current_trial_id.set(self._id)
        self._context.start()

    # cancel function should be called manually as a pair of start
    # FIXME: watch for system signals to cancel the trial gracefully,
    # or it could lead to trial not being marked as finished.
    def cancel(self):
        self._context.cancel()

    def _stop(self):
        trial = self._runtime._metadb.get_trial(trial_id=self._id)
        if trial is not None and trial.status not in COMPLETED_STATUS:
            duration = (
                datetime.now(UTC) - trial.created_at.replace(tzinfo=UTC)
            ).total_seconds()
            self._runtime._metadb.update_trial(
                trial_id=self._id, status=TrialStatus.FINISHED, duration=duration
            )

        self._runtime.current_exp.unregister_trial(self._id)
        self._runs.clear()
        for task in self._running_tasks.values():
            task.cancel()
        self._running_tasks.clear()

    def _get_obj(self):
        return self._runtime._metadb.get_trial(trial_id=self._id)

    def increment_step(self) -> int:
        self._step += 1
        return self._step

    def start_run(self, call_func: callable) -> Run:
        """Start a new run for the trial.
        :param call_func: a callable function that returns a coroutine.
                          It must be a async and lambda function.
        :return: the Run instance."""

        run = Run(trial_id=self._id)
        task = run._start(call_func)
        if task is None:
            raise RuntimeError("Failed to start the run task.")
        self._runs[run.id] = run
        self._running_tasks[run.id] = task

        task.add_done_callback(lambda t: self._running_tasks.pop(run.id, None))
        task.add_done_callback(lambda t: self._runs.pop(run.id, None))
        if self._config.max_runs_per_trial > 0:
            task.add_done_callback(
                lambda t: (
                    setattr(self, "_total_runs_counter", self._total_runs_counter + 1),
                    self.cancel()
                    if self._total_runs_counter >= self._config.max_runs_per_trial
                    else None,
                )
            )

        return run
