# Testing Guide

## Test Categories

- Unit tests (default): no live API required.
- Live smoke tests: optional, marked with `live`.

## Setup

1. Create `.env` in the project root (or export environment variables directly).
2. Set:
   - `GCD_SECRET_ID`
   - `GCD_SECRET_KEY`
3. Use sandbox institutions for development whenever possible.

## Commands

Run fast unit tests:

```bash
uv run pytest tests -m "not live" -v
```

Run live smoke tests:

```bash
uv run pytest tests -m live -v
```

Run only config flow tests:

```bash
uv run pytest tests/test_config_flow.py -v
```

## Notes

- Live tests consume API quota; keep them as smoke checks.
- Unit tests should cover coordinator orchestration, sensor projection, and flow behavior.


