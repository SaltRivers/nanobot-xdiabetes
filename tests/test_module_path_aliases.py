"""Compatibility tests for historical import paths.

These checks guarantee that the repository can present a cleaner internal
layout without breaking older import paths that existing integrations may still
use.
"""

from __future__ import annotations

import importlib


def test_clinical_package_aliases_resolve_to_same_module_object() -> None:
    canonical_pkg = importlib.import_module("xdiabetes.clinical")
    legacy_pkg = importlib.import_module("xdiabetes.x_diabetes")
    assert legacy_pkg is canonical_pkg

    canonical_workspace = importlib.import_module("xdiabetes.clinical.workspace")
    legacy_workspace = importlib.import_module("xdiabetes.x_diabetes.workspace")
    assert legacy_workspace is canonical_workspace


def test_tool_package_aliases_resolve_to_same_module_object() -> None:
    canonical_pkg = importlib.import_module("xdiabetes.agent.tools.diabetes")
    legacy_pkg = importlib.import_module("xdiabetes.agent.tools.xdiabetes")
    assert legacy_pkg is canonical_pkg

    canonical_tool = importlib.import_module("xdiabetes.agent.tools.diabetes.guideline_search")
    legacy_tool = importlib.import_module("xdiabetes.agent.tools.xdiabetes.guideline_search")
    assert legacy_tool is canonical_tool


def test_cli_entry_alias_resolves_to_primary_app_module() -> None:
    canonical_module = importlib.import_module("xdiabetes.cli.app")
    legacy_module = importlib.import_module("xdiabetes.cli.x_diabetes_entry")
    assert legacy_module is canonical_module
