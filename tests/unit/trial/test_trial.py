# ruff: noqa: E501

import time
import unittest
import uuid

import faker
import pytest

from alphatrion.trial.trial import CheckpointConfig, Trial, TrialConfig


class TestTrial(unittest.IsolatedAsyncioTestCase):
    @pytest.mark.asyncio
    async def test_timeout(self):
        test_cases = [
            {
                "name": "No timeout",
                "config": TrialConfig(),
                "created": False,
                "expected": None,
            },
            {
                "name": "Positive timeout",
                "config": TrialConfig(max_execution_seconds=10),
                "created": False,
                "expected": 10,
            },
            {
                "name": "Zero timeout",
                "config": TrialConfig(max_execution_seconds=0),
                "created": False,
                "expected": 0,
            },
            {
                "name": "Negative timeout",
                "config": TrialConfig(max_execution_seconds=-5),
                "created": False,
                "expected": None,
            },
            {
                "name": "With started_at, positive timeout",
                "config": TrialConfig(max_execution_seconds=5),
                "created": True,
                "expected": 3,
            },
        ]

        for case in test_cases:
            with self.subTest(name=case["name"]):
                trial = Trial(exp_id=uuid.uuid4(), config=case["config"])
                trial._start(name=faker.Faker().word())

                if case["created"]:
                    time.sleep(2)  # simulate elapsed time
                    self.assertEqual(
                        trial._timeout(), case["config"].max_execution_seconds - 2
                    )
                else:
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
