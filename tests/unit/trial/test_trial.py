import os
import unittest
from datetime import UTC, datetime, timedelta

from alphatrion.trial.trial import Trial, TrialConfig


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
                "config": TrialConfig(max_duration_seconds=10),
                "started_at": None,
                "expected": 10,
            },
            {
                "name": "Zero timeout",
                "config": TrialConfig(max_duration_seconds=0),
                "started_at": None,
                "expected": 0,
            },
            {
                "name": "Negative timeout",
                "config": TrialConfig(max_duration_seconds=-5),
                "started_at": None,
                "expected": None,
            },
            {
                "name": "With started_at, positive timeout",
                "config": TrialConfig(max_duration_seconds=5),
                "started_at": (
                    datetime.now(UTC) - timedelta(seconds=3)
                ).isoformat(),
                "expected": 2,
            },
        ]

        for case in test_cases:
            if case["started_at"]:
                os.environ["ALPHATRION_TRIAL_START_TIME"] = case["started_at"]
            with self.subTest(name=case["name"]):
                trial = Trial(exp_id=1, config=case["config"])
                self.assertEqual(trial._timeout(), case["expected"])
