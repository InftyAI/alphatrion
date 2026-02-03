import enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from alphatrion.experiment.base import current_exp_id
from alphatrion.run.run import current_run_id
from alphatrion.runtime.runtime import global_runtime

"""The snapshot is organized in a hierarchical directory structure as follows:
└── snapshots
    ├── team_26c73273-dc1f-40f2-a4ed-7eee35ae05d4
    │   └── project_7481eedd-86be-4d39-9d0d-679ba83ab7b6
    │       └── user_95eb9982-56fd-4e1a-8498-28312f4d3ba5
    │           └── exp_e5b08511-eba4-4ee7-bd10-e632110996b5
    │               └── run_5b08673b-b2cb-41fb-90f0-c15b450f4433
    └── team_dcafdce3-dfde-47b4-994c-93880848ca91
        ├── project_449a560d-cc12-46eb-9058-351cfe56433b
        │   ├── user_450704dd-37f4-4aa7-97f8-b34e42576b09
        │   │   ├── exp_c855725d-891f-4f61-8f7d-b6f40c94509f
        │   │   └── exp_f751ec9c-4aa2-46c5-8cab-1f92af6f001d
        │   │       ├── checkpoints
        │   │       ├── run_94a82594-01a7-463f-b63b-ab896be9830e
        │   │       │   └── record.json
        │   │       └── run_c0e3c730-c213-4a8e-9e10-7af57fcf8bf9
        │   └── user_f303c129-c4b5-4f24-957c-d28dd78cce89
        │       └── exp_efeb5430-6593-4675-969c-325aa25af986
        │           ├── run_1c89b44d-15de-464a-9e1c-c6aab8a82a7d
        │           └── run_7990bcf3-f864-4442-ae35-00dd8329f7c5
        └── project_5cb62b0b-83d3-49fa-956e-cd51df3e7891
"""


class RecordKind(enum.Enum):
    RUN = "run"
    # CUSTOM_RECORD_DEFINITION = "crd"


# time information is recorded in the metadata database,
# we can not get the endtime in the run.
class Metadata(BaseModel):
    id: str


class Spec(BaseModel):
    parameters: dict[str, Any]
    input: dict[str, Any] | None = None


class Result(BaseModel):
    output: dict[str, Any]


class Record(BaseModel):
    schema_version: str
    kind: RecordKind
    metadata: Metadata
    spec: Spec
    result: Result


def build_run_record(
    output: dict[str, Any], input: dict[str, Any] | None = None
) -> Record:
    run_id = current_run_id.get()
    run_obj = global_runtime().metadb.get_run(run_id=run_id)
    if run_obj is None:
        raise RuntimeError(f"Run {run_id} not found in the database.")

    exp_obj = global_runtime().metadb.get_experiment(
        experiment_id=run_obj.experiment_id
    )
    if exp_obj is None:
        raise RuntimeError(
            f"Experiment {run_obj.experiment_id} not found in the database."
        )

    record = Record(
        schema_version="1.0",
        kind=RecordKind.RUN,
        metadata=Metadata(
            id=str(run_id),
        ),
        spec=Spec(parameters=exp_obj.params or {}, input=input or {}),
        result=Result(
            output=output,
        ),
    )
    return record


def snapshot_path() -> str:
    runtime = global_runtime()
    return (
        Path(runtime.root_path)
        / "snapshots"
        / f"team_{runtime.team_id}"
        / f"project_{runtime.current_proj.id}"
        / f"user_{runtime.user_id}"
        / f"exp_{current_exp_id.get()}"
        / f"run_{current_run_id.get()}"
    )


def checkpoint_path() -> str:
    runtime = global_runtime()
    return (
        Path(runtime.root_path)
        / "snapshots"
        / f"team_{runtime.team_id}"
        / f"project_{runtime.current_proj.id}"
        / f"user_{runtime.user_id}"
        / f"exp_{current_exp_id.get()}"
        / "checkpoints"
    )


def team_path() -> str:
    runtime = global_runtime()
    return Path(runtime.root_path) / "snapshots" / f"team_{runtime.team_id}"
