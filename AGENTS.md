# Repository Guidelines

## Project Structure & Module Organization
This repository is currently a clean starting point for simulation work. Keep the layout predictable as code is added:

- `src/`: simulation code, environment wrappers, controllers, and utilities
- `tests/`: unit and integration tests mirroring `src/`
- `configs/`: experiment, simulator, and training configuration files
- `assets/`: robot models, meshes, scenes, and other static resources
- `scripts/`: reproducible entry points such as setup, training, or evaluation scripts

Example:
```text
src/dkk_simulation/
tests/test_env.py
configs/base.yaml
scripts/run_sim.py
```

## Build, Test, and Development Commands
No build system is committed yet. Use the project Conda environment first:

```bash
conda activate dkk_simulation
```

When running Python in this repository, prefer the `dkk_simulation` Conda environment rather than the system interpreter or `base`. This applies to scripts, tests, package installation, and one-off debugging commands.

Recommended commands once code is added:

- `python -m pytest`: run the full test suite
- `python -m pytest tests/test_env.py`: run one test module
- `python -m pip install -e .`: install the package in editable mode
- `python scripts/run_sim.py`: run a local simulation entry point

If you introduce a formatter, linter, or task runner, document the exact commands here and keep them stable.

## Coding Style & Naming Conventions
Use 4-space indentation for Python. Prefer type hints on public APIs and keep modules focused. Follow these naming rules:

- modules and packages: `snake_case`
- classes: `PascalCase`
- functions and variables: `snake_case`
- constants: `UPPER_SNAKE_CASE`

Prefer small, composable modules over large notebooks or monolithic scripts. If `ruff`, `black`, or similar tools are added later, use repository defaults rather than personal overrides.

## Testing Guidelines
Place tests under `tests/` and name them `test_*.py`. Mirror source paths where practical, for example `src/dkk_simulation/env.py` -> `tests/test_env.py`.

Add tests for new simulation logic, config parsing, and failure cases. For bugs, add a regression test before or with the fix.

## Commit & Pull Request Guidelines
This repository does not yet have Git history, so use a simple convention from the start: short, imperative commit subjects such as `Add Mujoco env wrapper` or `Fix reset seed handling`.

Pull requests should include:

- a clear summary of behavior changes
- linked issue or task ID when available
- setup or reproduction steps
- screenshots or logs for UI or simulator-visual changes

## Configuration & Assets
Do not commit secrets, local machine paths, or large generated outputs. Keep heavyweight assets out of Git unless they are required to reproduce the simulation setup.
