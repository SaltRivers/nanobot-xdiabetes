"""Shared constants for the X-Diabetes profile.

This module intentionally keeps all user-facing defaults in one place so the
runtime, tools, and workspace bootstrap stay consistent.
"""

from __future__ import annotations

DEFAULT_XDIABETES_WORKSPACE = "~/.nanobot/xdiabetes-workspace"
DEFAULT_CASE_ID = "demo_patient"
DEFAULT_KNOWLEDGE_LIMIT = 3
DEFAULT_REPORT_FILENAME_PREFIX = "xdiabetes_report"
DEFAULT_DTMH_BACKEND = "mock"
DEFAULT_PATIENT_MEMORY_DIR = "patient_memory"

ROOT_TEMPLATE_FILES = ("AGENTS.md", "USER.md", "TOOLS.md")
DIRECTORY_TEMPLATES = (
    "cases",
    "knowledge",
    "playbooks",
    "reports",
    "rules",
    "memory",
    "patient_memory",
    "skills",
)

SUPPORTED_DTMH_BACKENDS = {"mock", "python", "http", "mcp", "disabled"}
SUPPORTED_XDIABETES_MODES = {"doctor", "patient"}
SUPPORTED_TASKS = {
    "general",
    "screening",
    "subtyping",
    "complication",
    "management",
    "followup",
}
