from alphatrion.experiment import base


class CraftExperiment(base.Experiment):
    """
    CraftExperiment represents an experiment for crafting tasks.
    """

    def __init__(self, config: base.ExperimentConfig | None = None):
        super().__init__(config)

    @classmethod
    def start(
        cls,
        name: str,
        description: str | None = None,
        meta: dict | None = None,
        params: dict | None = None,
        config: base.ExperimentConfig | None = None,
    ) -> "CraftExperiment":
        """
        If the name is same in the same experiment,
        it will refer to the existing experiment.
        """

        exp = cls(config=config)
        exp._start(
            name=name,
            description=description,
            meta=meta,
            params=params,
        )

        return exp
