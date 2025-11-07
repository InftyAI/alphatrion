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

**AlphaTrion** is an open-source and all-in-one platform to build LLM-powered applications and frameworks. Named after the oldest and wisest Transformer mentor, it embodies guidance and innovation to help developers build **production-ready** GenAI applications and frameworks with ease. *Still under active development.*

## Concepts

- **Experiment**: An Experiment is a high-level abstraction for organizing and managing a series of related trials. It serves as a way to group together multiple trials that share a common goal or objective.
- **Trial**: A Trial represents a single attempt or multiple iterations within an experiment. It encapsulates the configuration, execution, and results of a specific set of runs.
- **Run**: A Run is an execution of a specific configuration within a trial. It represents a real iteration of the trial.

## Quick Start

### Install from PyPI

```bash
pip install alphatrion
```

### Run a Sample Experiment

Below is a simple example demonstrating how to create an experiment and log parameters, metrics, and artifacts.

```python
import alphatrion as alpha

alpha.init(project_id=<your_project_id>, artifact_insecure=True, init_tables=True)

async with alpha.CraftExperiment.start(name="my_first_experiment") as exp:
  async with exp.start_trial(name="my_first_trial") as trial:

    trial.start_run(lambda: alpha.log_parameters({"learning_rate": 0.01}))
    trial.start_run(lambda: alpha.log_metrics({"accuracy": 0.9}))
    trial.start_run(lambda: alpha.log_artifact(paths="file.txt", version="v1"))

    await trial.wait()
```

## Contributing

We welcome contributions! Please refer to [developer.md](./site/docs/development.md) for more information on how to set up your development environment and contribute to the project.

[![Star History Chart](https://api.star-history.com/svg?repos=inftyai/alphatrion&type=Date)](https://www.star-history.com/#inftyai/alphatrion&Date)