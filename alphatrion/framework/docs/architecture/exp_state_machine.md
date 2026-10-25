# Experiment Status State Machine

## Overview

The `Status` enum is shared between **Experiments** and **Runs**:

```python
class Status(enum.IntEnum):
    UNKNOWN = 0
    PENDING = 1
    RUNNING = 2
    COMPLETED = 9
    CANCELLED = 10    # User intentionally stopped, cannot resume
    FAILED = 11       # Recoverable: can retry after fixing error
    ABORTED = 12      # Programmatically aborted, cannot resume
    INTERRUPTED = 13  # Recoverable: system stopped (e.g. preemption), can resume
```

**Experiment statuses**: All values above
**Run statuses**: Subset only (RUNNING, COMPLETED, CANCELLED, FAILED)

## State Diagram

```
                             ┌─────────────┐
                             │ Experiment  │
                             └──────┬──────┘
                                    │
                                    ▼
                             ┌─────────────┐
                  ┌──────────│   PENDING   │
                  │          └──────┬──────┘
                  │                 │
                  │ abort()         │ start()
                  │                 │
                  ▼                 ▼
            ┌────────────┐   ┌─────────────┐
            │  ABORTED   │   │   RUNNING   │ ◀───────────────────────────────────────────┐
            └────────────┘   └──────┬──────┘                                             │
             (terminal)             │                                                    │
                                    │                                                    │
        ┌───────────────────────────┼───────────────────────────────────────┐            │
        │                           │                 │                     │            │
        │                           │                 │                     │            │
cancel()/signal(SIGINT)           done()           exception          signal(SIGTERM)    │
        │                           │            (unintentional)            │            │
        ▼                           ▼                 ▼                     ▼            │
  ┌────────────┐             ┌────────────┐     ┌────────────┐      ┌──────────────┐     │
  │ CANCELLED  │             │ COMPLETED  │     │   FAILED   │      │ INTERRUPTED  │     │
  └────────────┘             └────────────┘     └─────┬──────┘      └──────┬───────┘     │
   (terminal)                 (terminal)              │                    │             │
                                                      │                    │             │
                                                      └────────────────────┘             │
                                                                │              resume    │
                                                                └────────────────────────┘


────────────────────────────────────────────────────────────────────────────────────────
Terminal States (No Resume):
  • COMPLETED   - Success, finished normally
  • CANCELLED   - User stopped permanently (SIGINT/Ctrl+C or stopExperiment API)
  • ABORTED     - Validation failed before starting (only from PENDING state)

Recoverable States (Can Resume):
  • FAILED      - Exception/error during execution, can retry after fix
  • INTERRUPTED - System stopped (SIGTERM/K8s pod termination), can resume after restart
────────────────────────────────────────────────────────────────────────────────────────
```

## State Categories

| Category | States | Can Resume? | Description |
|----------|--------|-------------|-------------|
| **Active** | PENDING, RUNNING | N/A | Normal execution flow |
| **Terminal** | COMPLETED, CANCELLED, ABORTED | ❌ No | Final states, immutable |
| **Recoverable** | FAILED, INTERRUPTED | ✅ Yes | Can resume to RUNNING |

### Semantics

**Resumability is the key distinction:**

- **COMPLETED**: Success, nothing more to do
- **CANCELLED**: User decided to stop permanently (SIGINT in local dev, or stopExperiment API)
- **ABORTED**: Validation failed before starting (only from PENDING via stopExperiment API)
- **FAILED**: Unintentional error, retry after fixing
- **INTERRUPTED**: System event (SIGTERM from K8s pod termination, preemption), resume when restarted

## Implementation

### Constants

```python
# In sql_models.py
TERMINAL_STATUS = [Status.COMPLETED, Status.CANCELLED, Status.ABORTED]
RECOVERABLE_STATUS = [Status.FAILED, Status.INTERRUPTED]
FINISHED_STATUS = TERMINAL_STATUS + RECOVERABLE_STATUS
RUN_STATUS = [Status.RUNNING, Status.COMPLETED, Status.CANCELLED, Status.FAILED]
```
