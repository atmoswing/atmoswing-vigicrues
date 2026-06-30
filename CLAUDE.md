# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`atmoswing-vigicrues` is a Python package that orchestrates AtmoSwing flood forecasts for the French Vigicrues network. It is a pipeline driver: it does not produce forecasts itself but wraps the external `atmoswing-forecaster` binary, preparing its inputs (pre-actions), running it as a subprocess, post-processing its NetCDF outputs (post-actions), and shipping the results out (disseminations). There are no hard-coded parameters — everything is driven by a YAML config file, so multiple independent forecast flows coexist as separate config files on one machine.

Note: code, docstrings, and user-facing messages are in **French**. Match that language when editing existing code.

## Commands

```bash
# Run a forecast flow (the primary entry point)
python -m atmoswing_vigicrues --config-file="path/to/config.yaml"
python -m atmoswing_vigicrues -c config.yaml -d 2023060100 -i 6   # specific date + time increment

# Tests
pytest                          # full suite
pytest tests/test_controller.py # single file
pytest tests/test_controller.py::test_controller_instance_succeeds  # single test

# Lint / format (also enforced via pre-commit)
flake8 .                        # max-line-length = 88
black .
pre-commit run --all-files

# Install for development
pip install -e ".[dev,tests]"
```

### Important about tests
Tests that actually run AtmoSwing or SFTP are gated behind module-level flags that default to **False**: `RUN_ATMOSWING` and `RUN_SFTP` (see `tests/test_controller.py`). Without them, those tests only exercise construction/configuration, not the real external binary or network transfer. `RUN_ATMOSWING` needs a local AtmoSwing Forecaster install and a `DATA_PATH` that points to a private dataset; `RUN_SFTP` needs a running SFTP docker container. Do not assume these flags can be flipped on in CI.

## Architecture

The flow is fixed and lives in `Controller.run()` (`src/atmoswing_vigicrues/controller.py`):

1. **pre-actions** → 2. **AtmoSwing forecast** (subprocess) → 3. **post-actions** → 4. **disseminations**

Key pieces:

- **`Controller`** — owns the run. Resolves the forecast `date` (floored to a multiple of `time_increment`, default 6h, via `_fix_date`), discovers AtmoSwing output files by date-stamped glob, builds and runs the forecaster command line (`_build_atmoswing_cmd`), and on failure prints the forecaster log from the temp dir. Catches all exceptions in `run()` and returns a non-zero code rather than raising.
- **`Options`** (`options.py`) — merges CLI args with the YAML config (loaded with `yaml.FullLoader`). Use `options.has(key)` / `options.get(key)`; `get` raises `OptionError` if missing.
- **Plugin registration** — actions are not imported directly. The controller reads `pre_actions` / `post_actions` / `disseminations` lists from the config, and for each entry looks up the class named in its `uses:` field via `getattr(importlib.import_module('atmoswing_vigicrues'), uses)`. **This means every action class must be exported from `src/atmoswing_vigicrues/__init__.py`** or it will be reported as unknown. Each entry's `with:` dict is passed to the class constructor. An `active: False` entry is skipped.

### Action base classes and contracts

Three families, each a subclass tree under its own subpackage:

- **`PreAction`** (`preactions/`) — `run(date) -> bool`. The controller retries the whole pre-action set with a back-in-time loop: if any pre-action returns False, the forecast date steps back by `attempts_step_hours` and retries up to `attempts_max_hours` (set via `_set_attempts_attributes`). Implementations: `DownloadGfsData`, `TransformGfsData`, `TransformEcmwfData`, `TransferSftpIn`.
- **`PostAction`** (`postactions/`) — `feed(file_paths, metadata)` then `run() -> bool`. Operates on the NetCDF files AtmoSwing just produced. Implementations: `ExportBdApBp` (JSON), `ExportPrv`.
- **`Dissemination`** (`disseminations/`) — exposes `local_dir` and `extension` attributes (the controller uses them to glob files), then `feed(file_paths)` and `run(date) -> bool`. Implementations: `TransferSftpOut`, `TransferFtpOut`.

When adding a new action: subclass the right base, set `self.type_name` and `self.name` in `__init__`, read everything from the `options` dict, export the class in `__init__.py`, and reference it by class name in the config's `uses:` field.

### Conventions worth knowing

- **Date-based directory layout**: files are organized as `base/YYYY/MM/DD` via `utils.build_date_dir_structure`, and SFTP/FTP transfers recreate that structure remotely. File discovery globs `YYYY-MM-DD_HH.*<ext>`.
- **Optional heavy deps** are guarded at import time in `__init__.py` (`has_netcdf`, `has_eccodes`); `eccodes`, `pandas`, and `atmoswing-toolbox` live in `requirements-optional.txt`, not the core `requirements.txt`.
- **Errors** use the hierarchy in `exceptions.py` (`Error` base, plus `OptionError`, `ConfigError`, `PathError`, `FilePathError`). Path checks go through `utils.check_file_exists` / `check_dir_exists` / `file_exists`.
- **Config files may contain special characters** (e.g. passwords with accents/symbols) — there is a test guarding this; preserve UTF-8 handling.

## Deployment

Packaged to PyPI and as a Docker image built `FROM atmoswing/forecaster` (the Dockerfile installs this module on top of the forecaster image, so the binary is already on PATH). Version is set in both `pyproject.toml` and `setup.py` — keep them in sync, and update `changelog.md` (in French).
