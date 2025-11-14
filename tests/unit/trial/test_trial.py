# ruff: noqa: E501

import os
import unittest
from datetime import UTC, datetime, timedelta

from alphatrion.trial.trial import CheckpointConfig, Trial, TrialConfig


class TestTrial(unittest.IsolatedAsyncioTestCase):
    def test_timeout(self):
        test_cases = [
            {
                "name": "No timeout",
                "config": TrialConfig(),
                "started_at": None,
                "expected": None,
            },
            {
                "name": "Positive timeout",
                "config": TrialConfig(max_runtime_seconds=10),
                "started_at": None,
                "expected": 10,
            },
            {
                "name": "Zero timeout",
                "config": TrialConfig(max_runtime_seconds=0),
                "started_at": None,
                "expected": 0,
            },
            {
                "name": "Negative timeout",
                "config": TrialConfig(max_runtime_seconds=-5),
                "started_at": None,
                "expected": None,
            },
            {
                "name": "With started_at, positive timeout",
                "config": TrialConfig(max_runtime_seconds=5),
                "started_at": (datetime.now(UTC) - timedelta(seconds=3)).isoformat(),
                "expected": 2,
            },
        ]

        for case in test_cases:
            if case["started_at"]:
                os.environ["ALPHATRION_TRIAL_START_TIME"] = case["started_at"]
            with self.subTest(name=case["name"]):
                trial = Trial(exp_id=1, config=case["config"])
                self.assertEqual(trial._timeout(), case["expected"])

    def test_config(self):
        test_cases = [
            {
                "name": "Default config",
                "config": {
                    "checkpoint.save_on_best": False,
                    "early_stopping_runs": -1,
                },
                "error": False,
            },
            {
                "name": "save_on_best True config",
                "config": {
                    "monitor_metric": "accuracy",
                    "checkpoint.save_on_best": True,
                    "early_stopping_runs": 2,
                },
                "error": False,
            },
            {
                "name": "Invalid config missing monitor_metric",
                "config": {
                    "checkpoint.save_on_best": True,
                    "early_stopping_runs": -1,
                },
                "error": True,
            },
            {
                "name": "Invalid config early_stopping_runs > 0",
                "config": {
                    "checkpoint.save_on_best": False,
                    "early_stopping_runs": 2,
                },
                "error": True,
            },
        ]

        for case in test_cases:
            with self.subTest(name=case["name"]):
                if case["error"]:
                    with self.assertRaises(ValueError):
                        Trial(
                            exp_id=1,
                            config=TrialConfig(
                                monitor_metric=case["config"].get(
                                    "monitor_metric", None
                                ),
                                checkpoint=CheckpointConfig(
                                    save_on_best=case["config"].get(
                                        "checkpoint.save_on_best", False
                                    ),
                                ),
                                early_stopping_runs=case["config"].get(
                                    "early_stopping_runs", -1
                                ),
                            ),
                        )
                else:
                    _ = Trial(
                        exp_id=1,
                        config=TrialConfig(
                            monitor_metric=case["config"].get("monitor_metric", None),
                            checkpoint=CheckpointConfig(
                                save_on_best=case["config"].get(
                                    "checkpoint.save_on_best", False
                                ),
                            ),
                            early_stopping_runs=case["config"].get(
                                "early_stopping_runs", -1
                            ),
                        ),
                    )
