from .types import Experiment, Metric, Project, Run, Trial


class GraphQLResolvers:
    @staticmethod
    def list_projects() -> list[Project]:
        return []

    @staticmethod
    def get_project(id: str) -> Project | None:
        return None

    @staticmethod
    def list_experiments() -> list[Experiment]:
        return []

    @staticmethod
    def get_experiment(id: str) -> Experiment | None:
        return None

    @staticmethod
    def list_trials(experiment_id: str) -> list[Trial]:
        return []

    @staticmethod
    def get_trial(id: str) -> Trial | None:
        return None

    @staticmethod
    def list_runs(trial_id: str) -> list[Run]:
        return []

    @staticmethod
    def get_run(id: str) -> Run | None:
        return None

    @staticmethod
    def list_trial_metrics(trial_id: str) -> list[Metric]:
        return []
