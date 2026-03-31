"""Shared constants for the X-Diabetes profile.

This module intentionally keeps all user-facing defaults in one place so the
runtime, tools, and workspace bootstrap stay consistent.
"""

from __future__ import annotations

DEFAULT_X_DIABETES_WORKSPACE = "~/.x-diabetes/x-diabetes-workspace"
DEFAULT_KNOWLEDGE_LIMIT = 3
DEFAULT_REPORT_FILENAME_PREFIX = "xdiabetes_report"
DEFAULT_DTMH_BACKEND = "http"
DEFAULT_PATIENT_MEMORY_DIR = "patient_memory"
DEFAULT_LEARNING_DIR = "learning"

ROOT_TEMPLATE_FILES = ("AGENTS.md", "USER.md", "TOOLS.md")
DIRECTORY_TEMPLATES = (
    "cases",
    "knowledge",
    "learning",
    "playbooks",
    "reports",
    "rules",
    "memory",
    "patient_memory",
    "skills",
)
LEARNING_DIRECTORY_TEMPLATES = (
    "observations",
    "instincts",
    "drafts",
    "evaluations/instincts",
    "evaluations/drafts",
    "evaluations/activations",
    "approved",
    "rejected",
    "rollback",
    "state",
    "policies",
    "evals",
)

SUPPORTED_DTMH_BACKENDS = {"mock", "python", "http", "mcp", "disabled"}
SUPPORTED_X_DIABETES_MODES = {"doctor", "patient"}
SUPPORTED_TASKS = {
    "general",
    "screening",
    "subtyping",
    "complication",
    "management",
    "followup",
}
