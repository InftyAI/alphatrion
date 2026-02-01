# TODO: Implement snapshot in the future if the content size is really big.
class Snapshot:
    """Represents a snapshot of the current state of the system.
    The snapshot is organized in a hierarchical directory structure as follows:

    └── snapshot
        ├── team_1c273580-5dec-4e30-b136-f1caf9d8bdb1
        └── team_dcafdce3-dfde-47b4-994c-93880848ca91
            ├── project_449a560d-cc12-46eb-9058-351cfe56433b
            │   ├── user_450704dd-37f4-4aa7-97f8-b34e42576b09
            │   │   ├── exp_c855725d-891f-4f61-8f7d-b6f40c94509f
            │   │   └── exp_f751ec9c-4aa2-46c5-8cab-1f92af6f001d
            │   │       ├── config.yaml
            │   │       ├── run_94a82594-01a7-463f-b63b-ab896be9830e
            │   │       │   ├── code.json
            │   │       │   ├── log.jsonl
            │   │       │   └── prompt.json
            │   │       └── run_c0e3c730-c213-4a8e-9e10-7af57fcf8bf9
            │   └── user_f303c129-c4b5-4f24-957c-d28dd78cce89
            │       └── exp_efeb5430-6593-4675-969c-325aa25af986
            │           ├── run_1c89b44d-15de-464a-9e1c-c6aab8a82a7d
            │           └── run_7990bcf3-f864-4442-ae35-00dd8329f7c5
            └── project_5cb62b0b-83d3-49fa-956e-cd51df3e7891
    """

    pass
