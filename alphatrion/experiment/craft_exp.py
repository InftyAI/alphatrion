from alphatrion.experiment.base import Experiment, ExperimentConfig


class CraftExperiment(Experiment):
    """
    Craft experiment implementation.

    This experiment class offers methods to manage the experiment lifecycle flexibly.
    Opposite to other experiment classes, you need to call all these methods yourself.
    """

    def __init__(self, config: ExperimentConfig | None = None):
        super().__init__(config=config)
        # Disable auto-checkpointing by default for CraftExperiment
        self._config.checkpoint.enabled = False
