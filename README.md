<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/inftyai/alphatrion/main/site/images/alphatrion.png">
    <img alt="alphatrion" src="https://raw.githubusercontent.com/inftyai/alphatrion/main/site/images/alphatrion.png" width=55%>
  </picture>
</p>

<h3 align="center">
Open, modular framework to build GenAI applications.
</h3>

[![stability-alpha](https://img.shields.io/badge/stability-alpha-f4d03f.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#alpha)
[![Latest Release](https://img.shields.io/github/v/release/inftyai/alphatrion?include_prereleases)](https://github.com/inftyai/alphatrion/releases/latest)

**AlphaTrion** is an open-source framework to help build GenAI applications, including experiment tracking, adaptive model routing, prompt optimization, performance evaluation and so on. The name comes after the oldest and wisest Transformer - AlphaTrion.

*Still under active development.*

## Concepts

- **Project**: A Project is a namespace-level abstraction that isolates experiments from different users or teams.
- **Experiment**: An Experiment is a logic-level abstraction for organizing and managing a series of related trials. It serves as a way to group together multiple trials that share a common goal or objective.
- **Trial**: A Trial represents a config-level abstraction for a specific set of hyperparameters or configurations within an experiment. It is a single execution of a particular configuration.
- **Run**: A Run is a real execution instance of a trial. It represents the actual execution of the code with the specified configuration and hyperparameters defined in the trial.

## Quick Start

### Install from PyPI

```bash
pip install alphatrion
```

### Install from Source

* Git clone the repository
* Run `source start.sh` to activate the virtual environment.


### Initialize the Environment

Run the following command for setup:

```bash
cp .env.example .env & make up
```
You can login to pgAdmin at `http://localhost:8081` to see the Postgres database with following credentials. Remember to register the server first.

```shell
Email:       alphatrion@inftyai.com
Password:    alphatr1on
ServerName:  alphatrion
HostName:    postgres
ServerPWD:   alphatr1on
```

### Run a Simple Experiment

Below is a simple example with two approaches demonstrating how to create an experiment and log performance metrics.

```python
import alphatrion as alpha
import uuid

# Better to use a fixed UUID to identify your project.
alpha.init(project_id=uuid.uuid4(), artifact_insecure=True)

async def log():
  # Run your code here then log metrics.
  await alpha.log_metrics({"accuracy": 0.95})

async with alpha.CraftExperiment.setup(name="my_experiment") as exp:
  async with exp.start_trial(name="my_trial") as trial:
    run = trial.start_run(lambda: log())
    await run.wait()
```

### View Dashboard

The dashboard is under active development.
You can already run the frontend locally to explore experiments, trials, runs, and metrics through the UI.

### Prerequisites
Make sure the following are installed:

- **Node.js ≥ 18**
- **npm ≥ 9**
- **Vite**

### Launch Dashboard

```bash
alphatrion server # Start the backend server
alphatrion dashboard # Start the dashboard
```
Dashboard is available at `http://localhost:3000` by default.

### Cleanup

```bash
make down
```

## Contributing

We welcome contributions! Please refer to [developer.md](./docs/dev/development.md) for more information on how to set up your development environment and contribute to the project.

[![Star History Chart](https://api.star-history.com/svg?repos=inftyai/alphatrion&type=Date)](https://www.star-history.com/#inftyai/alphatrion&Date)
