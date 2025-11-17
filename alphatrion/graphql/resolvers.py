from typing import List, Optional
from .types import Project, Experiment, Trial, Run, Metric


class GraphQLResolvers:

    @staticmethod
    def get_projects() -> List[Project]:
        return []

    @staticmethod
    def get_project(id: str) -> Optional[Project]:
        return None

    @staticmethod
    def get_experiments() -> List[Experiment]:
        return []

    @staticmethod
    def get_experiment(id: str) -> Optional[Experiment]:
        return None

    @staticmethod
    def get_trials(experiment_id: str) -> List[Trial]:
        return []

    @staticmethod
    def get_trial(id: str) -> Optional[Trial]:
        return None

    @staticmethod
    def get_runs(trial_id: str) -> List[Run]:
        return []

    @staticmethod
    def get_run(id: str) -> Optional[Run]:
        return None

    @staticmethod
    def get_trial_metrics(trial_id: str) -> List[Metric]:
        return []
