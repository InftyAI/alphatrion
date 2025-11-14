from alphatrion.experiment.base import Experiment, ExperimentConfig
from alphatrion.trial.trial import Trial, TrialConfig


class CraftExperiment(Experiment):
    """
    Craft experiment implementation.

    This experiment class offers methods to manage the experiment lifecycle flexibly.
    Opposite to other experiment classes, you need to call all these methods yourself.
    """

    def __init__(self, config: ExperimentConfig | None = None):
        super().__init__(config=config)

    @classmethod
    def setup(
        cls,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        config: ExperimentConfig | None = None,
    ) -> "CraftExperiment":
        """
        Setup the experiment. If the name already exists in the same project,
        it will refer to the existing experiment instead of creating a new one.
        """

        exp = CraftExperiment(config=config)
        exp_obj = exp._get_by_name(name=name, project_id=exp._runtime._project_id)

        # If experiment with the same name exists in the project, use it.
        if exp_obj:
            exp._id = exp_obj.uuid
        else:
            exp._create(
                name=name,
                description=description,
                meta=meta,
            )

        return exp

    def start_trial(
        self,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
        config: TrialConfig | None = None,
    ) -> Trial:
        """
        start_trial starts a new trial in this experiment.
        You need to call trial.cancel() to stop the trial for proper cleanup,
        unless it's a timeout trial.
        Or you can use 'async with exp.start_trial(...) as trial', which will
        automatically stop the trial at the end of the context.

        :params description: the description of the trial
        :params meta: the metadata of the trial
        :params config: the configuration of the trial

        :return: the Trial instance
        """

        config = config or TrialConfig()

        if (
            self._config is not None
            and self._config.max_runtime_seconds > 0
            and config.max_runtime_seconds < 0
        ):
            config.max_runtime_seconds = self._config.max_runtime_seconds

        trial = Trial(exp_id=self._id, config=config)
        trial._start(name=name, description=description, meta=meta, params=params)
        self.register_trial(id=trial.id, instance=trial)
        return trial
