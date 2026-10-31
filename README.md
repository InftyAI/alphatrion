<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/inftyai/alphatrion/main/site/images/alphatrion.png">
    <img alt="alphatrion" src="https://raw.githubusercontent.com/inftyai/alphatrion/main/site/images/alphatrion.png" width=55%>
  </picture>
</p>

<h3 align="center">
Open-source recursive self-improvement system.
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

**AlphaTrion** is an open-source project to build **recursive self-improvement (RSI)**: AI systems that get better at their tasks, and also get better at improving themselves. Every attempt is treated as an experiment that is run, measured, versioned, and traceable, so you can see exactly how the system improved and why. Named after the oldest and wisest Transformer.

## Components

| Component | Status | Description |
|---|---|---|
| [Framework](./alphatrion/framework) | Beta | The infrastructure for running and tracking experiments: experiments and runs, an artifact registry, metrics and distributed tracing, and a dashboard. Reusable on its own for any LLM application. |
| [Swarm](./alphatrion/swarm) | Early development | The recursive self-improvement system, built on the framework. |

## Installation

```bash
# The framework only (either command)
pip install alphatrion
pip install alphatrion[framework]

# The framework and swarm
pip install alphatrion[all]
```

To start tracking experiments today, see the [framework README](./alphatrion/framework/README.md). For runnable code, see the [examples](./examples).

## Development

```bash
git clone https://github.com/inftyai/alphatrion.git && cd alphatrion
source start.sh
make test
```

See the [development guide](./alphatrion/framework/docs/development.md) for details.

## Contributing

AlphaTrion is in its early days, and contributions are very welcome, from ideas and design discussions to code. See the [contributing guide](./CONTRIBUTING.md) to get started.

## License

Apache-2.0. See [LICENSE](./LICENSE).

[![Star History Chart](https://api.star-history.com/svg?repos=inftyai/alphatrion&type=Date)](https://www.star-history.com/#inftyai/alphatrion&Date)
