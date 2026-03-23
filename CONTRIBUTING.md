# Contributing to X-Diabetes

Thank you for contributing.

We want X-Diabetes to stay focused, readable, and dependable. Prefer small, well-scoped changes that improve the clinical workflow without adding unnecessary complexity.

## Branching Guidance

| Change Type | Preferred Target |
|-------------|------------------|
| New feature | `nightly` |
| Refactor | `nightly` |
| Bug fix with no behavior change | `main` |
| Documentation | `main` |
| Unsure | `nightly` |

## Development Setup

```bash
# Clone this repository
cd <repo-dir>

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint code
ruff check xdiabetes/

# Format code
ruff format xdiabetes/
```

## Code Style

Please aim for code that is:

- simple
- clear
- well-bounded
- easy to test
- easy to maintain

Project defaults:

- Python 3.11+
- `ruff` for linting and formatting
- max line length 100
- `pytest` with `asyncio_mode = "auto"`

## Practical Expectations

- Prefer the smallest safe patch.
- Keep runtime behavior stable unless the change explicitly intends otherwise.
- Avoid broad rewrites when a local fix is enough.
- Add or update tests when behavior is touched.
- Keep user-facing text aligned with the X-Diabetes product name.

## Questions

If anything is unclear, open an issue or contact the maintainers listed in repository materials.

Thanks again for your time and care.
