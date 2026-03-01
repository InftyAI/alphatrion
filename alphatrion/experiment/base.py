import asyncio
import contextlib
import enum
import os
import shutil
import signal
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

from alphatrion import envs
from alphatrion.run.run import Run
from alphatrion.runtime.contextvars import current_exp_id
from alphatrion.runtime.runtime import global_runtime
from alphatrion.snapshot.snapshot import team_path
from alphatrion.storage.sql_models import FINISHED_STATUS, Status
from alphatrion.types import CallableEntry
from alphatrion.utils import context


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
    # save_every_n_runs: int = Field(
    #     default=-1,
    #     description="Interval in runs to save checkpoints. \
    #         Default is -1 (unlimited).",
    # )
    save_on_best: bool = Field(
        default=False,
        description="Once a best result is found, it will be saved. \
            The metric to monitor is specified by monitor_metric. Default is False. \
            Can be enabled together with save_every_n_steps/save_every_n_seconds.",
    )
    path: str | None = Field(
        default=None,
        description="The path to save checkpoints. \
                     If None, will be under the specified experiment directory. \
                     Call snapshot.checkpoint_path() to get the path. Remember to \
                     create the directory if it does not exist. It's lazy created.",
    )
    pre_save_hook: Callable | None = Field(
        default=None,
        description="A callable function to be called before saving a checkpoint. \
            The function should take no arguments. You can use partial if you want. \
            If you want to save something, make sure it's under the checkpoint path. \
            Default is None. ",
    )


class MonitorMode(enum.Enum):
    MAX = "max"
    MIN = "min"


class ExperimentConfig(BaseModel):
    """Configuration for a Experiment."""

    max_execution_seconds: int = Field(
        default=-1,
        description="Maximum execution seconds for the Experiment. \
        Default is -1 (no limit).",
    )
    early_stopping_runs: int = Field(
        default=-1,
        description="Number of runs with no improvement \
        after which the Experiment will be stopped. Default is -1 (no early stopping). \
        Count each time when calling log_metrics with the monitored metric.",
    )
    max_runs_per_experiment: int = Field(
        default=-1,
        description="Maximum number of runs for each Experiment. \
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
        description="If specified, the Experiment will stop when \
            the monitored metric reaches this target value. \
            If monitor_mode is 'max', the Experiment will stop when \
            the metric >= target_metric_value. If monitor_mode is 'min', \
            the Experiment will stop when the metric <= target_metric_value. \
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


class Experiment(ABC):
    """
    Base Experiment class. An Experiment manages multiple Runs and their configurations.
    """

    __slots__ = (
        "_id",
        "_config",
        "_runtime",
        "_context",
        "_token",
        # _meta stores the runtime meta information of the experiment.
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
        # Only work when max_runs_per_experiment > 0
        "_total_runs_counter",
        # The end status, None, Err or Cancelled.
        "_end_status",
        "_stopped",
        "_signal_task",
    )

    def __init__(self, config: ExperimentConfig | None = None):
        self._config = config or ExperimentConfig()

        self._runtime = global_runtime()
        self._runtime.current_experiment = self

        self._construct_meta()
        self._runs = dict[uuid.UUID, Run]()
        self._early_stopping_counter = 0
        self._total_runs_counter = 0
        self._end_status = None
        # if experiment starts to wait, it will auto stop when the runs
        # are all finished.
        self._start_waiting = False
        self._end_status = None
        self._stopped = asyncio.Event()
        self._signal_task: asyncio.Task | None = None

    async def __aenter__(self):
        self._signal_task = self._start_signal_handlers()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.done()
        self._end_status = None

        if self._signal_task:
            # Already done, will not update the status again.
            self._signal_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await self._signal_task

        if self._token:
            current_exp_id.reset(self._token)
            self._runtime.current_experiment = None

    def _start(
        self,
        name: str,
        description: str | None = None,
        labels: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
    ):
        exp_obj = self._runtime.metadb.get_exp_by_name(
            name=name, team_id=self._runtime.team_id
        )

        # Just in case of kubernetes pod restarts, we want to make sure the experiment
        # can be resumed if it is not completed, instead of creating a new experiment
        # with the same name. If the experiment is already completed, we raise an error
        # to avoid confusion.
        if exp_obj and exp_obj.status != Status.COMPLETED:
            self._id = exp_obj.uuid
        elif exp_obj and exp_obj.status == Status.COMPLETED:
            raise RuntimeError(
                f"Experiment with name '{name}' already exists and is completed. \
                Please choose a different name or delete the existing experiment."
            )
        else:
            self._id = self._runtime._metadb.create_experiment(
                name=name,
                team_id=self._runtime._team_id,
                user_id=self._runtime._user_id,
                description=description,
                labels=labels,
                meta=meta,
                params=params,
                status=Status.RUNNING,
            )

        self._context = context.Context(
            cancel_func=self._stop,
            timeout=self._timeout(),
        )

        self._token = current_exp_id.set(self._id)

    @property
    def id(self) -> uuid.UUID:
        return self._id

    def _construct_meta(self):
        self._meta = dict()

        # TODO: if restart from existing experiment,
        # load the best_metrics from database.
        if self._config.monitor_mode == MonitorMode.MAX:
            self._meta["best_metrics"] = {self._config.monitor_metric: float("-inf")}
        elif self._config.monitor_mode == MonitorMode.MIN:
            self._meta["best_metrics"] = {self._config.monitor_metric: float("inf")}
        else:
            raise ValueError(f"Invalid monitor_mode: {self._config.monitor_mode}")

    def config(self) -> ExperimentConfig:
        return self._config

    def should_checkpoint_on_best(
        self, metric_key: str, metric_value: float
    ) -> tuple[bool, bool]:
        is_best_metric = self.save_if_best_metric(metric_key, metric_value)
        return (self._checkpoint_on_best_enabled() and is_best_metric), is_best_metric

    def _checkpoint_on_best_enabled(self) -> bool:
        return self._config.checkpoint.enabled and self._config.checkpoint.save_on_best

    def save_if_best_metric(self, metric_key: str, metric_value: float) -> bool:
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
    # automatically, however, this is unpredictable because some tasks may wait for
    # external events, so we leave it to the user to decide when to stop the experiment.
    async def wait(self):
        self._start_waiting = True
        await self._context.wait()

    def is_done(self) -> bool:
        return self._context.cancelled()

    # done function should be called manually as a pair of start
    # FIXME: watch for system signals to cancel the Experiment gracefully,
    # or it could lead to experiment not being marked as completed.
    # TODO: Should we distinguish done and cancel?
    def done(self):
        self._cancel()
        self._cleanup()

    def done_with_err(self):
        self._end_status = "Err"
        self.done()

    def done_with_cancel(self):
        self._end_status = "Cancelled"
        self.done()

    def _cancel(self):
        self._context.cancel()

    def _stop(self):
        # cancel the runs first, then stop the experiment.
        for run in self._runs.values():
            # When experiment is stopped, we consider the unfinished runs as cancelled.
            run.cancel()
        self._runs.clear()

        exp = self._runtime._metadb.get_experiment(experiment_id=self.id)
        if exp is not None and exp.status not in FINISHED_STATUS:
            duration = (
                datetime.now(UTC) - exp.created_at.replace(tzinfo=UTC)
            ).total_seconds()

            status = Status.COMPLETED
            if self._end_status == "Err":
                status = Status.FAILED
            elif self._end_status == "Cancelled":
                status = Status.CANCELLED

            self._runtime.metadb.update_experiment(
                experiment_id=self._id, status=status, duration=duration
            )

    def _get_obj(self):
        return self._runtime._metadb.get_experiment(experiment_id=self.id)

    def run(self, call_func: CallableEntry) -> Run:
        """Start a new run for the Experiment.
        :param call_func: a callable function that returns a coroutine.
                          It must be a async and lambda function.
        :return: the Run instance."""

        # Check if experiment is already done. This usually happens when we
        # cancel the experiment with Ctrl+C directly.
        if self.is_done():
            raise RuntimeError(
                f"Cannot create new run: Experiment {self.id} is already completed."
            )

        run = Run(exp_id=self.id)
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
            self._config.max_runs_per_experiment > 0
            and self._total_runs_counter >= self._config.max_runs_per_experiment
        ):
            self.done()

        # If the experiment starts to wait and all runs are finished,
        # we can stop the experiment.
        if self._start_waiting and len(self._runs) == 0:
            self.done()

    @classmethod
    @abstractmethod
    def start(
        cls,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
    ) -> "Experiment":
        raise NotImplementedError

    def _cleanup(self):
        # remove the whole folder once the experiment is done.
        if (
            os.path.exists(team_path())
            and os.getenv(envs.AUTO_CLEANUP, "true").lower() == "true"
        ):
            shutil.rmtree(team_path(), ignore_errors=True)

    def _start_signal_handlers(self):
        loop = asyncio.get_running_loop()

        # Handle SIGINT and SIGTERM to allow graceful shutdown.
        # Make sure to call done() on receiving the signal.
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._on_signal)

        return asyncio.create_task(self._wait_for_stop())

    def _on_signal(self):
        self._stopped.set()

    async def _wait_for_stop(self):
        await self._stopped.wait()
        self.done_with_cancel()
