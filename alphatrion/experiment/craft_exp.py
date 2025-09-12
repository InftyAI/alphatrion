from alphatrion.experiment.base import Experiment
from alphatrion.runtime.runtime import Runtime


class CraftExperiment(Experiment):
    """
    Craft experiment implementation.

    This experiment class offers methods to manage the experiment lifecycle flexibly.
    Opposite to other experiment classes, you need to call all these methods yourself.
    """

    def __init__(self, runtime: Runtime):
        super().__init__(runtime)
        # Disable checkpointing by default for CraftExperiment
        self._config.checkpoint.enabled = False
