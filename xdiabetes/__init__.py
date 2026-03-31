"""X-Diabetes runtime package.

This package keeps a stable public import surface even when internal modules
are reorganized. Historical module paths are bridged to the current canonical
implementation so existing integrations and tests continue to work unchanged.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
from typing import Final

__version__ = "0.1.4.post5"
__logo__ = "🩺"


class _ModuleAliasFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Map historical module paths onto the canonical package layout."""

    def __init__(self, aliases: dict[str, str]):
        self._aliases = dict(sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True))

    def _resolve(self, fullname: str) -> str | None:
        for old_prefix, new_prefix in self._aliases.items():
            if fullname == old_prefix:
                return new_prefix
            if fullname.startswith(f"{old_prefix}."):
                suffix = fullname[len(old_prefix):]
                return f"{new_prefix}{suffix}"
        return None

    def find_spec(self, fullname: str, path=None, target=None):  # type: ignore[override]
        target_name = self._resolve(fullname)
        if target_name is None:
            return None

        target_spec = importlib.util.find_spec(target_name)
        if target_spec is None:
            return None

        is_package = target_spec.submodule_search_locations is not None
        return importlib.util.spec_from_loader(fullname, self, is_package=is_package)

    def create_module(self, spec):  # type: ignore[override]
        target_name = self._resolve(spec.name)
        if target_name is None:
            return None

        module = importlib.import_module(target_name)
        sys.modules[spec.name] = module
        return module

    def exec_module(self, module) -> None:  # type: ignore[override]
        """The canonical module is already loaded in ``create_module``."""


_MODULE_ALIASES: Final[dict[str, str]] = {
    "xdiabetes.x_diabetes": "xdiabetes.clinical",
    "xdiabetes.agent.tools.xdiabetes": "xdiabetes.agent.tools.diabetes",
    "xdiabetes.cli.x_diabetes_entry": "xdiabetes.cli.app",
}


def _register_module_aliases() -> None:
    """Install the compatibility bridge exactly once."""
    if any(isinstance(finder, _ModuleAliasFinder) for finder in sys.meta_path):
        return
    sys.meta_path.insert(0, _ModuleAliasFinder(_MODULE_ALIASES))


_register_module_aliases()
