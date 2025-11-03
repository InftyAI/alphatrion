import uuid

from alphatrion.experiment.base import Experiment
from alphatrion.trial.trial import Trial, TrialConfig


class CraftExperiment(Experiment):
    """
    Craft experiment implementation.

    This experiment class offers methods to manage the experiment lifecycle flexibly.
    Opposite to other experiment classes, you need to call all these methods yourself.
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def run(
        cls,
        name: str,
        id: uuid.UUID | None = None,
        description: str | None = None,
        meta: dict | None = None,
    ) -> "CraftExperiment":
        """
        Begin the experiment. This method must be used to start multi-trial experiment.
        If id is provided, the experiment with the given id will be used.
        """

        exp = CraftExperiment()

        if id is not None:
            exp._id = id
        else:
            exp._create(
                name=name,
                description=description,
                meta=meta,
            )

        return exp

    def start_trial(
        self,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
        config: TrialConfig | None = None,
    ) -> Trial:
        """
        start_trial starts a new trial in this experiment.
        You need to call trial.stop() to stop the trial for proper cleanup,
        unless it's a timeout trial. Or you can use 'with exp.run_trial(...)' as trial,
        which will automatically stop the trial at the end of the context.

        :params description: the description of the trial
        :params meta: the metadata of the trial
        :params config: the configuration of the trial

        :return: the Trial instance
        """

        trial = Trial(exp_id=self._id, config=config)
        trial._start(description=description, meta=meta, params=params)
        self.register_trial(id=trial.id, instance=trial)
        return trial
