"""Built-in post-run hooks for metadata enrichment."""

import uuid
from typing import Any

from alphatrion.runtime.runtime import global_runtime


class PostRunHookFn:
    """Library of built-in post-run hooks."""

    @staticmethod
    def sync_metadata(run_id: uuid.UUID, result: Any) -> None:
        """
        Sync function result to run metadata.

        If the function returns a dict, it will be merged into the run's metadata.
        This is useful for automatically capturing metrics, model info, etc.

        Example:
            async def train_model():
                # ... training code ...
                return {
                    "accuracy": 0.95,
                    "loss": 0.05,
                    "num_epochs": 10,
                }

            run = exp.run(train_model, post_run_hooks=[PostRunHookFn.sync_metadata])
            # After completion, run metadata will contain accuracy, loss, num_epochs

        :param run_id: UUID of the run
        :param result: Return value from the run function
        """
        if isinstance(result, dict):
            metadb = global_runtime().metadb
            metadb.update_run(run_id=run_id, meta=result)
