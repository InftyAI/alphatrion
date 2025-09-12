from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, field_validator

from alphatrion.runtime.runtime import Runtime


class CheckpointConfig(BaseModel):
    """Configuration for a checkpoint."""

    enabled: bool = Field(
        default=True,
        description="Whether to enable checkpointing. \
            Default is True.",
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


class Experiment(ABC):
    """Base class for all experiments."""

    def __init__(self, runtime: Runtime, config: ExperimentConfig | None = None):
        self._runtime = runtime
        self._config = config or ExperimentConfig()

    @abstractmethod
    def create(
        self,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        labels: dict | None = None,
    ):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def delete(self, exp_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get(self, exp_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def list(self, page: int = 0, page_size: int = 10):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def update_labels(self, exp_id: int, labels: dict):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def start(self, exp_id: int):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def stop(self, exp_id: int, status: str = "finished"):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def status(self, exp_id: int) -> str:
        raise NotImplementedError("Subclasses must implement this method.")
