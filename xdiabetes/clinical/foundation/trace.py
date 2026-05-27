"""Workflow execution trace logging and persistence.

This module captures the complete clinical reasoning process for
debugging, auditing, and research demonstration.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from xdiabetes.clinical.foundation.schemas import FoundationTrace


class TraceLogger:
    """Workflow trace logging and persistence engine."""

    def __init__(self, workspace_dir: str | Path | None = None):
        """Initialize the trace logger.

        Args:
            workspace_dir: Optional workspace directory for trace storage
        """
        self.workspace_dir = Path(workspace_dir) if workspace_dir else None

    def create_trace(
        self,
        trace_id: str,
        patient_id: str,
        original_query: str,
    ) -> FoundationTrace:
        """Create a new workflow trace.

        Args:
            trace_id: Unique trace identifier
            patient_id: Patient identifier
            original_query: Original user query

        Returns:
            New FoundationTrace object
        """
        return FoundationTrace(
            trace_id=trace_id,
            patient_id=patient_id,
            original_query=original_query,
            created_at=datetime.now(UTC),
        )

    async def save_trace(
        self,
        trace: FoundationTrace,
        output_dir: str | Path | None = None,
    ) -> str:
        """Save workflow trace to disk.

        Args:
            trace: FoundationTrace to save
            output_dir: Optional output directory (defaults to workspace/runs/)

        Returns:
            Path to saved trace file
        """
        if output_dir is None:
            if self.workspace_dir is None:
                raise ValueError("No workspace directory configured")
            output_dir = self.workspace_dir / "runs"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = trace.created_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{trace.patient_id}_foundation_trace.json"
        filepath = output_path / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(trace.model_dump(), f, indent=2, default=str)

        return str(filepath)

    async def load_trace(self, filepath: str | Path) -> FoundationTrace:
        """Load workflow trace from disk.

        Args:
            filepath: Path to trace file

        Returns:
            Loaded FoundationTrace object
        """
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        return FoundationTrace(**data)
