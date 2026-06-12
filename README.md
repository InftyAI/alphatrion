<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/inftyai/alphatrion/main/site/images/alphatrion.png">
    <img alt="alphatrion" src="https://raw.githubusercontent.com/inftyai/alphatrion/main/site/images/alphatrion.png" width=55%>
  </picture>
</p>

<h3 align="center">
The open-source framework for LLM experiments and agent orchestration.
</h3>

<p align="center">
  <a href="https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#beta">
    <img src="https://img.shields.io/badge/stability-beta-f4d03f.svg" alt="Beta Stability">
  </a>
  <a href="https://pypi.org/project/alphatrion/">
    <img src="https://img.shields.io/pypi/v/alphatrion" alt="PyPI">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/github/license/inftyai/alphatrion" alt="License">
  </a>
</p>

**AlphaTrion** is an open-source experiment tracking and agent orchestration framework for LLM application developers and AI engineers. Orchestrate multi-agent workflows, track LLM experiments, manage artifacts, and gain deep observability into your GenAI applications—all through an intuitive Python API and modern dashboard. Named after the oldest and wisest Transformer.

### Trusted By

<a href="https://hiverge.ai" target="_blank">
  <img src="./site/images/hiverge-logo.svg" alt="Hiverge.ai" height="40">
</a>

## Key Features

- **🔬 Experiment Management** - Hierarchical experiments and runs with smart checkpointing (save on best metrics, early stopping, target optimization)
- **📦 Artifact Registry** - Version datasets and model checkpoints using OCI registries or S3, with native `push`/`pull` APIs
- **📊 Metrics & Observability** - Built-in Prometheus metrics and distributed tracing (OpenTelemetry + ClickHouse) for LLM calls
- **🪝 Extensible Hooks** - Pre/post-save hooks and post-run hooks for custom workflows
- **🎯 Modern Dashboard** - Explore experiments, visualize metrics, and analyze traces through an intuitive web UI
- **🔌 Production-Ready** - Async-first design, PostgreSQL metadata storage, and support for distributed workloads

## Core Concepts

- **Organization** - Top-level entity for grouping teams and users
- **Team** - Collaborative workspace for organizing experiments and runs
- **User** - Individual account with secure authentication and team memberships
- **Experiment** - Logical grouping of runs with shared purpose, organized by labels
- **Run** - Individual execution instance with configuration and metrics

## Quick Start

### 1. Installation

```bash
# From PyPI
pip install alphatrion

# Or from source
git clone https://github.com/inftyai/alphatrion.git && cd alphatrion
source start.sh
```

### 2. Setup

```bash
# Start PostgreSQL, ClickHouse, and Registry
cp .env.example .env
make up

# Wait for services to be ready, then run migrations
make migrate-all

# Initialize your organization, team, and user account
alphatrion init
```

**Optional Tools:**
- pgAdmin: `http://localhost:8081` (alphatrion@inftyai.com / alphatr1on)
- Registry UI: `http://localhost:80`
- Grafana: `http://localhost:3000` (admin / admin) - LLM metrics dashboard
- Prometheus: `http://localhost:9090` - Metrics explorer

### 3. Run Your First Experiment

```python
import alphatrion as alpha
from alphatrion.experiment import CraftExperiment

# Initialize with your user ID
alpha.init(user_id="<your_user_id>")

async def my_task():
    # Your code here
    await alpha.log_metrics({"accuracy": 0.95, "loss": 0.12})

async with CraftExperiment.start(name="my_experiment") as exp:
    run = exp.run(my_task)
    await exp.wait()
```

### 4. Launch Dashboard

```bash
# Start backend server (terminal 1)
alphatrion server

# Launch dashboard (terminal 2)
alphatrion dashboard
```

Access the dashboard at `http://127.0.0.1:5173` and **log in with your email and password** to explore experiments, visualize metrics, and analyze traces.

![dashboard](./site/images/dashboard.png)

### 5. Distributed Tracing

AlphaTrion provides decorators for instrumenting your code with OpenTelemetry distributed tracing:

- **`@tracing.workflow()`** - Top-level orchestration
- **`@tracing.agent()`** - Autonomous AI agents with decision-making
- **`@tracing.task()`** - Reusable units of work
- **`@tracing.tool()`** - Atomic leaf operations

All decorators automatically capture execution duration, status, span hierarchy, and context (run_id, experiment_id, team_id, org_id). LLM calls, database queries, and HTTP requests are auto-instrumented.

View captured traces in the dashboard:

![tracing](./site/images/trace.png)

### 6. Using Post-Run Hooks (Optional)

Automatically sync metadata and status after run completion.

```python
from alphatrion.experiment import CraftExperiment
from alphatrion.run import PostRunHookFn

async def train_model():
    # Your training code
    return {
        "metadata": {"accuracy": 0.95, "loss": 0.05},
        "status": "COMPLETED",
    }

async with CraftExperiment.start("training") as exp:
    run = exp.run(
        train_model,
        post_run_hooks=[PostRunHookFn.sync_metadata, PostRunHookFn.sync_status]
    )
    await exp.wait()
```

### 7. Cleanup

```bash
make down
```

## References

- **Architecture**: [Diagrams](./docs/architecture/diagrams.md)
- **Dashboard**: [Setup Guide](./docs/dashboard/setup.md) | [CLI Reference](./docs/dashboard/dashboard-cli.md) | [Architecture](./docs/dashboard/dashboard-architecture.md)
- **Development**: [Contributing Guide](./docs/dev/development.md)
- **Claude Code Integration**: [Hooks Setup](./docs/CLAUDE_CODE_HOOKS.md)

## Contributing

We welcome contributions! Check out our [development guide](./docs/dev/development.md) to get started.

[![Star History Chart](https://api.star-history.com/svg?repos=inftyai/alphatrion&type=Date)](https://www.star-history.com/#inftyai/alphatrion&Date)
