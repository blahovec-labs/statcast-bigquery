# Contributing

Bug reports + small PRs welcome. Please open an issue before large changes.

This is a hobbyist project; review cadence is best-effort.

## Dev setup

    uv venv
    uv pip install -e ".[dev]"
    pytest

## Style

Ruff + pyright. Run `ruff check . && pyright` before opening a PR.
