# Foundation Agent Testing Guide

## Task #9: Unit Tests for Foundation Agent Workflow

### Status
- **Test file created**: `tests/test_foundation_agent.py` (650+ lines, 20+ test cases)
- **Python 3.9 compatibility fixes applied**: Added `from __future__ import annotations` to multiple files
- **Dependencies identified**: Missing `pydantic-settings`, `json-repair`, `litellm`

### Prerequisites

Before running the tests, ensure all dependencies are installed:

```bash
# Install the project in development mode (recommended)
pip install -e ".[dev]"

# OR install missing dependencies individually
pip install pydantic-settings json-repair litellm
```

### Testing Commands

#### Run all Foundation Agent tests
```bash
python -m pytest tests/test_foundation_agent.py -v
```

#### Run specific test modules
```bash
# ClinicalPlanner tests
python -m pytest tests/test_foundation_agent.py::test_planner_decomposes_screening_query -v
python -m pytest tests/test_foundation_agent.py::test_planner_classifies_risk_assessment_query -v
python -m pytest tests/test_foundation_agent.py::test_planner_extracts_patient_reference -v
python -m pytest tests/test_foundation_agent.py::test_planner_generates_guideline_plan -v

# DataManager tests
python -m pytest tests/test_foundation_agent.py::test_data_manager_csv_mode -v
python -m pytest tests/test_foundation_agent.py::test_data_manager_case_mode_with_complete_data -v
python -m pytest tests/test_foundation_agent.py::test_data_manager_detects_missing_critical_fields -v
python -m pytest tests/test_foundation_agent.py::test_data_manager_validates_age_range -v

# DTMHOrchestrator tests
python -m pytest tests/test_foundation_agent.py::test_orchestrator_creates_execution_plan_csv_mode -v
python -m pytest tests/test_foundation_agent.py::test_orchestrator_maps_capabilities -v

# ClinicalInterpreter tests
python -m pytest tests/test_foundation_agent.py::test_interpreter_high_risk_screening -v
python -m pytest tests/test_foundation_agent.py::test_interpreter_low_risk_screening -v
python -m pytest tests/test_foundation_agent.py::test_interpreter_critical_risk_screening -v
python -m pytest tests/test_foundation_agent.py::test_interpreter_extracts_data_limitations -v

# WorkflowReflector tests
python -m pytest tests/test_foundation_agent.py::test_reflector_complete_workflow -v
python -m pytest tests/test_foundation_agent.py::test_reflector_detects_insufficient_data -v
python -m pytest tests/test_foundation_agent.py::test_reflector_detects_model_uncertainty -v
python -m pytest tests/test_foundation_agent.py::test_reflector_detects_data_quality_issues -v
python -m pytest tests/test_foundation_agent.py::test_reflector_generates_task_specific_reasons -v
```

#### Run with verbose output and stop on first failure
```bash
python -m pytest tests/test_foundation_agent.py -xvs
```

#### Run with coverage report
```bash
python -m pytest tests/test_foundation_agent.py --cov=xdiabetes.clinical.foundation --cov-report=html
```

### Files Modified for Python 3.9 Compatibility

The following files were updated with `from __future__ import annotations` to support Python 3.9:

1. `xdiabetes/utils/helpers.py`
2. `xdiabetes/agent/skills.py`
3. `xdiabetes/agent/context.py`
4. `xdiabetes/agent/tools/registry.py`
5. `xdiabetes/agent/tools/filesystem.py`
6. `xdiabetes/agent/tools/shell.py`
7. `xdiabetes/bus/events.py`
8. `xdiabetes/config/schema.py`
9. `xdiabetes/config/loader.py`
10. `xdiabetes/providers/base.py`

### Test Coverage

The test file covers all Foundation Agent modules:

#### ClinicalPlanner (4 tests)
- Query decomposition for diabetes screening
- Risk assessment query classification
- Patient reference extraction patterns
- Guideline-based workflow planning

#### DataManager (4 tests)
- CSV mode data preparation
- Case mode with complete patient data
- Missing critical field detection
- Age range validation

#### DTMHOrchestrator (2 tests)
- Execution plan creation for CSV mode
- Capability mapping for different task types

#### ClinicalInterpreter (4 tests)
- High-risk screening interpretation (85% probability)
- Low-risk screening interpretation (25% probability)
- Critical-risk screening interpretation (92% probability)
- Data limitations extraction

#### WorkflowReflector (6 tests)
- Complete workflow reflection
- Insufficient data detection
- Model uncertainty detection
- Data quality issues detection
- Task-specific completion reasons

### Expected Test Results

All tests should pass if:
1. All dependencies are installed
2. Python 3.9+ is being used
3. The Foundation Agent modules are correctly implemented

### Troubleshooting

#### Import Errors
If you see `ModuleNotFoundError`, install missing dependencies:
```bash
pip install <missing-module>
```

#### Type Errors with `|` operator
If you see `TypeError: unsupported operand type(s) for |`, ensure the file has:
```python
from __future__ import annotations
```
at the top (after the docstring).

#### Async Test Errors
Ensure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

### Next Steps After Tests Pass

Once all tests pass, proceed to:
- **Task #10**: Register FoundationWorkflow as primary clinical tool
- **Task #11**: Update SKILL.md with Foundation Agent workflow guidance
- **Task #12**: Update architecture documentation

### Notes

- Tests are designed to be independent and can run in any order
- No external services (DTMH HTTP endpoint) are required for unit tests
- Tests use mock data and do not require actual patient data
- All tests are async and use `@pytest.mark.asyncio` decorator
