"""Foundation Agent tool for X-Diabetes clinical workflows."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from xdiabetes.agent.tools.base import Tool
from xdiabetes.clinical.adapters.base import DTMHAdapter
from xdiabetes.clinical.foundation.workflow import FoundationWorkflow


class XDiabetesFoundationTool(Tool):
    """Foundation Agent workflow for guideline-grounded clinical reasoning.

    This tool orchestrates the complete clinical workflow:
    1. Query decomposition and guideline-based planning
    2. Data preparation and validation
    3. DTMH capability orchestration
    4. Clinical interpretation with evidence augmentation
    5. Reflective decision-making
    6. Clinical report generation

    This is the primary entry point for X-Diabetes clinical queries.
    """

    def __init__(self, *, dtmh_adapter: DTMHAdapter):
        """Initialize the Foundation Agent tool.

        Args:
            dtmh_adapter: DTMH adapter for model inference
        """
        self._workflow = FoundationWorkflow(dtmh_adapter=dtmh_adapter)

    @property
    def name(self) -> str:
        return "xdiabetes_foundation"

    @property
    def description(self) -> str:
        return (
            "Execute the X-Diabetes Foundation Agent workflow for clinical diabetes analysis. "
            "This tool provides guideline-grounded clinical reasoning with structured planning, "
            "DTMH model orchestration, clinical interpretation, and reflective decision-making. "
            "Use this for diabetes screening, risk assessment, and clinical decision support. "
            "Example: 'Check whether patient 4 in Dataset/private_fundus has diabetes'"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Clinical query in natural language (e.g., 'Check whether patient 4 in Dataset/private_fundus has diabetes')",
                },
                "patient_data": {
                    "type": "object",
                    "description": "Optional structured patient data dictionary",
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        query: str,
        patient_data: dict[str, Any] | None = None,
        **_: Any,
    ) -> str:
        """Execute the Foundation Agent workflow.

        Args:
            query: Clinical query in natural language
            patient_data: Optional patient data dictionary

        Returns:
            JSON string with workflow trace and clinical interpretation
        """
        logger.info("Foundation Agent executing query: {}", query[:100])

        # Execute workflow
        trace = await self._workflow.execute(
            query=query,
            patient_data=patient_data,
            context={},
        )

        # Build response
        response = {
            "trace_id": trace.trace_id,
            "patient_id": trace.patient_id,
            "task_type": trace.task_plan.task_type if trace.task_plan else "unknown",
            "clinical_conclusion": (
                trace.interpretation.main_conclusion if trace.interpretation else ""
            ),
            "risk_level": (
                trace.interpretation.risk_level if trace.interpretation else "unknown"
            ),
            "recommended_actions": (
                trace.interpretation.recommended_next_actions
                if trace.interpretation
                else []
            ),
            "workflow_complete": (
                trace.reflection.is_complete if trace.reflection else False
            ),
            "dtmh_backend": trace.dtmh_backend,
            "total_duration_ms": trace.total_duration_ms,
            "guideline_basis": (
                trace.guideline_plan.guideline_basis if trace.guideline_plan else []
            ),
            "clinical_steps": (
                trace.guideline_plan.clinical_steps if trace.guideline_plan else []
            ),
            "data_quality_flags": (
                trace.data_preparation.data_quality_flags
                if trace.data_preparation
                else []
            ),
            "warnings": trace.warnings,
        }

        logger.info(
            "Foundation Agent completed: trace_id={} duration={}ms",
            trace.trace_id,
            trace.total_duration_ms,
        )

        return json.dumps(response, indent=2, ensure_ascii=False)
