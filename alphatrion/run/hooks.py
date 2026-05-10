"""Built-in post-run hooks for metadata enrichment."""

import logging
import uuid
from typing import Any

from alphatrion.runtime.runtime import global_runtime
from alphatrion.storage.sql_models import Status

logger = logging.getLogger(__name__)


class PostRunHookFn:
    """Library of built-in post-run hooks."""

    @staticmethod
    def sync_metadata(run_id: uuid.UUID, result: Any) -> None:
        """
        Sync function result to run metadata.

        Looks for 'metadata' key in result dict and syncs it to run metadata.

        Example:
            async def train_model():
                return {
                    "metadata": {
                        "accuracy": 0.95,
                        "loss": 0.05,
                        "num_epochs": 10,
                    },
                    "status": "COMPLETED"
                }

            run = exp.run(train_model, post_run_hooks=[PostRunHookFn.sync_metadata])
            # After completion, run metadata will contain accuracy, loss, num_epochs

        :param run_id: UUID of the run
        :param result: Return value from the run function
        """
        if result is None:
            return

        if isinstance(result, dict) and "metadata" in result:
            metadata = result["metadata"]
            if isinstance(metadata, dict):
                metadb = global_runtime().metadb
                metadb.update_run(run_id=run_id, meta=metadata)
            else:
                logger.warning(
                    f"PostRunHookFn.sync_metadata: 'metadata' key in result for run {run_id} is not a dict. Skipping metadata sync."
                )
        else:
            logger.warning(
                f"PostRunHookFn.sync_metadata: Result for run {run_id} does not contain 'metadata' key or is not a dict. Skipping metadata sync."
            )

    @staticmethod
    def sync_status(run_id: uuid.UUID, result: Any) -> None:
        """
        Sync function result to run status and optional status_msg to metadata.

        Looks for 'status' key in result dict. Status can be a string representation,
        or integer value. Optionally looks for 'status_msg' key to store in metadata.

        Example:
            async def train_model():
                return {
                    "status": "COMPLETED",  # or 9
                    "status_msg": "Training completed successfully"
                }

            run = exp.run(train_model, post_run_hooks=[
                PostRunHookFn.sync_status
            ])

        :param run_id: UUID of the run
        :param result: Return value from the run function
        """
        if result is None:
            return

        status = None
        status_msg = None

        # Extract status and status_msg from dict
        if isinstance(result, dict):
            if "status" in result:
                status_value = result["status"]

                if isinstance(status_value, str):
                    try:
                        status = Status[status_value.upper()]
                    except (KeyError, AttributeError):
                        logger.warning(
                            f"PostRunHookFn.sync_status: Invalid status value '{status_value}' for run {run_id}. Skipping status sync."
                        )
                        return
                elif isinstance(status_value, int):
                    try:
                        status = Status(status_value)
                    except ValueError:
                        logger.warning(
                            f"PostRunHookFn.sync_status: Invalid status value '{status_value}' for run {run_id}. Skipping status sync."
                        )
                        return

            if "status_msg" in result:
                status_msg = result["status_msg"]

        # Update both status and status_msg in a single call if needed
        if status is not None or status_msg is not None:
            metadb = global_runtime().metadb
            update_kwargs = {}

            if status is not None:
                update_kwargs["status"] = status

            if status_msg is not None:
                update_kwargs["meta"] = {"status_msg": status_msg}

            metadb.update_run(run_id=run_id, **update_kwargs)
