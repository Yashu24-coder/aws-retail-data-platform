# Contributing

## Setup

```bash
pip install -r requirements-dev.txt
make run      # confirms the pipeline is green before you change anything
make test
```

## Before opening a pull request

1. `make test` - all 23 tests pass.
2. `make lint` - ruff is clean.
3. `make run` - 12 / 12 quality gates still pass.
4. If you changed a model, update `docs/data_dictionary.md`.
5. If you changed a rule in `quality/checks.yml`, say in the PR why the threshold
   is what it is.

## Adding a data quality check

Append to `quality/checks.yml`. The SQL must return a single number. Use
`severity: error` only for things that make the data wrong; use `warn` for
things worth knowing. `test_quality_rules.py` will fail if the SQL does not run,
which catches most typos before CI does.

## Commit messages

Imperative, specific, under 72 characters:

- `Add region-level revenue breakdown to mart_monthly_revenue`
- `Fix date parsing for rows with two-digit years`
- `Raise Athena scan cap to 2 GB for the analyst workgroup`
