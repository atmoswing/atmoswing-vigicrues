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
flake8 src tests                # max-line-length = 88 (same pinned versions as CI)
black .
pre-commit run --all-files

# Install for development
pip install -e ".[dev,tests]"
```

### Important about tests
Tests that need an external resource carry a pytest marker and are **skipped** (reported as such) unless the matching environment variable is `1` (see `tests/conftest.py`): `atmoswing` (`ASV_TEST_ATMOSWING`, needs a local AtmoSwing Forecaster and the private dataset at `ASV_TEST_DATA_PATH`), `sftp` (`ASV_TEST_SFTP`, running SFTP docker container), `ftp` (`ASV_TEST_FTP`), `network` (`ASV_TEST_NETWORK`, NOMADS downloads). Do not enable them in CI. Never gate a test with a module-level flag or an early `return`: it would pass silently.

The GRIB transformation tests are skipped unless `eccodes` and `atmoswing-toolbox` are installed; they only run in CI inside the Docker image (`build-docker-image.yml`). To run the full suite with eccodes locally: build the image and run `pytest` in it with the repo mounted.

## Architecture

The flow is fixed and lives in `Controller.run()` (`src/atmoswing_vigicrues/controller.py`):

1. **pre-actions** → 2. **AtmoSwing forecast** (subprocess) → 3. **post-actions** → 4. **disseminations**

Key pieces:

- **`Controller`** — owns the run. Resolves the forecast `date` (floored to a multiple of `time_increment`, default 6h, via `_fix_date`), discovers AtmoSwing output files by date-stamped glob, builds and runs the forecaster command line (`_build_atmoswing_cmd`), and on failure prints the forecaster log from the temp dir. Catches all exceptions in `run()` and returns a non-zero code rather than raising.
- **`Options`** (`options.py`) — merges CLI args with the YAML config (loaded with `yaml.safe_load`). Use `options.has(key)` / `options.get(key)`; `get` raises `OptionError` if missing.
- **Plugin registration** — actions are not imported directly. `Controller._register_actions` reads the `pre_actions` / `post_actions` / `disseminations` lists from the config and, for each entry, looks up the class named in its `uses:` field on the `atmoswing_vigicrues` package; it must be a subclass of that section's base class. **This means every action class must be exported from `src/atmoswing_vigicrues/__init__.py`** or it will be reported as unknown (`ConfigError`). Each entry's `with:` dict is passed to the class constructor; a missing required option (`KeyError`) becomes a `ConfigError` naming the action. An `active: False` entry is skipped. Configuration errors are reported by `__main__` (exit code `-1`) without a traceback.

### Action base classes and contracts

Three families, each an `abc.ABC` subclass tree under its own subpackage (`run` is abstract):

- **`PreAction`** (`preactions/`) — `run(date) -> bool`. The controller retries the whole pre-action set with a back-in-time loop: if any pre-action returns False, the forecast date steps back by `attempts_step_hours` and retries up to `attempts_max_hours` (set via `_set_attempts_attributes`). Implementations: `DownloadGfsData`, `TransferSftpIn`, and `TransformGfsData` / `TransformEcmwfData`, which share `TransformGribData` (`transform_grib.py`; subclasses only define the GRIB file pattern, `dataset_tag` and `type_name`).
- **`PostAction`** (`postactions/`) — `feed(file_paths, metadata)` then `run() -> bool`. Operates on the NetCDF files AtmoSwing just produced. Implementations: `ExportBdApBp` (JSON), `ExportPrv`.
- **`Dissemination`** (`disseminations/`) — exposes `local_dir` and `extension` attributes (the controller uses them to glob files), then `feed(file_paths)` and `run(date) -> bool`. Implementations: `TransferSftpOut`, `TransferFtpOut`.

When adding a new action: subclass the right base, set `self.type_name` and `self.name` in `__init__`, read everything from the `options` dict, export the class in `__init__.py`, and reference it by class name in the config's `uses:` field.

### Conventions worth knowing

- **Date-based directory layout**: files are organized as `base/YYYY/MM/DD` via `utils.build_date_dir_structure`, and SFTP/FTP transfers recreate that structure remotely. File discovery globs `YYYY-MM-DD_HH.*<ext>`.
- **Optional heavy deps** are guarded at import time in `__init__.py` (`has_netcdf`, `has_eccodes`) and `transform_grib.py` (`has_toolbox`); `eccodes`, `pandas`, and `atmoswing-toolbox` live in `requirements-optional.txt` / the `grib` extra, not the core dependencies.
- **eccodes definitions in Docker**: the forecaster base image sets `ECCODES_DEFINITION_PATH` for its older system eccodes; the pip `eccodes` bundles a newer library that cannot decode with those definitions. `utils.use_builtin_eccodes_definitions()` (called at package import) overrides the path for the Python process only, via the eccodes API — never change `os.environ` for this, the forecaster subprocess needs the variable.
- **Logging**: never `print`. Each module uses `logger = logging.getLogger(__name__)` (`INFO` for progress, `WARNING`/`ERROR` for failures). Only `__main__.configure_logging()` configures output (stdout, `%(asctime)s %(levelname)s %(message)s`, package at `INFO`, third parties at `WARNING`); the library itself never adds handlers. Tests check messages with `caplog` (INFO needs `caplog.set_level(logging.INFO, logger='atmoswing_vigicrues')`); `tests/conftest.py` undoes `main()`'s configuration after each test.
- **Errors** use the hierarchy in `exceptions.py` (`Error` base, plus `OptionError`, `ConfigError`, `PathError`, `FilePathError`). Path checks go through `utils.check_file_exists` / `check_dir_exists` / `file_exists`.
- **Config files may contain special characters** (e.g. passwords with accents/symbols) — there is a test guarding this; preserve UTF-8 handling.

## Deployment

Packaged to PyPI and as a Docker image built `FROM atmoswing/forecaster` (the Dockerfile installs this module on top of the forecaster image, so the binary is already on PATH). Packaging metadata, dependencies and the version live only in `pyproject.toml` (no `setup.py`/`setup.cfg`); keep `requirements*.txt` in sync with its `dependencies` / `optional-dependencies` (used by CI and the Dockerfile), and update `changelog.md` (in French).

Exit codes of `Controller.run()` (propagated by `__main__`): `0` success, `1` forecast produced but a post-action or dissemination failed, `-1` fatal (pre-actions exhausted all attempts, AtmoSwing failed, or an exception).
