"""Unit tests for Foundation Agent modules."""

from __future__ import annotations

from typing import Any

import pytest

from xdiabetes.clinical.foundation.data_manager import DataManager
from xdiabetes.clinical.foundation.dtmh_orchestrator import DTMHOrchestrator
from xdiabetes.clinical.foundation.interpreter import ClinicalInterpreter
from xdiabetes.clinical.foundation.planner import ClinicalPlanner
from xdiabetes.clinical.foundation.reflector import WorkflowReflector
from xdiabetes.clinical.foundation.schemas import (
    ClinicalInterpretation,
    ClinicalTaskPlan,
    DTMHExecutionPlan,
    DataPreparationResult,
)


# ============================================================================
# ClinicalPlanner Tests
# ============================================================================


@pytest.mark.asyncio
async def test_planner_decomposes_screening_query():
    """Test query decomposition for diabetes screening."""
    planner = ClinicalPlanner()

    query = "Check whether patient 4 in Dataset/private_fundus has diabetes"
    task_plan = await planner.decompose_query(query)

    assert task_plan.original_query == query
    assert task_plan.task_type == "screening"
    assert task_plan.patient_reference == "4"
    assert task_plan.required_dtmh_capability == "diabetes_screening"
    assert "demographics" in task_plan.required_data
    assert "labs" in task_plan.required_data


@pytest.mark.asyncio
async def test_planner_classifies_risk_assessment_query():
    """Test query classification for risk assessment."""
    planner = ClinicalPlanner()

    query = "What is the complication risk for patient 123?"
    task_plan = await planner.decompose_query(query)

    assert task_plan.task_type == "risk_assessment"
    assert task_plan.patient_reference == "123"
    assert task_plan.required_dtmh_capability == "complication_prediction"


@pytest.mark.asyncio
async def test_planner_extracts_patient_reference():
    """Test patient reference extraction patterns."""
    planner = ClinicalPlanner()

    # Test various patterns
    queries = [
        ("patient 4", "4"),
        ("patient ID 123", "123"),
        ("pt 99", "99"),
        ("for patient ABC-123", "ABC-123"),
    ]

    for query, expected_id in queries:
        task_plan = await planner.decompose_query(f"Check {query}")
        assert task_plan.patient_reference == expected_id


@pytest.mark.asyncio
async def test_planner_generates_guideline_plan():
    """Test guideline-based workflow planning."""
    planner = ClinicalPlanner()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 4",
        task_type="screening",
        audience="doctor",
        patient_reference="4",
        required_data=["demographics", "labs"],
        required_dtmh_capability="diabetes_screening",
    )

    guideline_plan = await planner.plan_workflow(task_plan)

    assert len(guideline_plan.clinical_steps) >= 4
    assert "ADA Standards of Medical Care in Diabetes" in guideline_plan.guideline_basis
    assert "data_quality_validation" in guideline_plan.required_safety_checks
    assert "diabetes_probability" in guideline_plan.expected_dtmh_outputs


# ============================================================================
# DataManager Tests
# ============================================================================


@pytest.mark.asyncio
async def test_data_manager_csv_mode():
    """Test data preparation in CSV mode."""
    manager = DataManager()

    task_plan = ClinicalTaskPlan(
        original_query="Check patient 4 in Dataset/private_fundus",
        task_type="screening",
        audience="doctor",
        patient_reference="4",
        required_data=["demographics", "labs"],
        required_dtmh_capability="diabetes_screening",
    )

    result = await manager.prepare_data(task_plan)

    assert result.patient_id == "4"
    assert result.dtmh_ready is True
    assert "cohort_csv" in result.available_modalities
    assert result.payload_preview["mode"] == "csv"
    assert result.payload_preview["cohort_dir"] == "Dataset/private_fundus"


@pytest.mark.asyncio
async def test_data_manager_case_mode_with_complete_data():
    """Test data preparation with complete patient data."""
    manager = DataManager()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 123",
        task_type="screening",
        audience="doctor",
        patient_reference="123",
        required_data=["demographics", "labs", "vitals"],
        required_dtmh_capability="diabetes_screening",
    )

    patient_data = {
        "demographics": {"age": 45, "sex": "male"},
        "labs": {"hba1c": 7.2},
        "vitals": {"sbp": 130, "dbp": 85},
    }

    result = await manager.prepare_data(task_plan, patient_data)

    assert result.patient_id == "123"
    assert result.dtmh_ready is True
    assert "demographics" in result.available_modalities
    assert "labs" in result.available_modalities
    assert "vitals" in result.available_modalities
    assert len(result.missing_fields) == 0
    assert len(result.data_quality_flags) == 0


@pytest.mark.asyncio
async def test_data_manager_detects_missing_critical_fields():
    """Test detection of missing critical fields."""
    manager = DataManager()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 123",
        task_type="screening",
        audience="doctor",
        patient_reference="123",
        required_data=["demographics", "labs"],
        required_dtmh_capability="diabetes_screening",
    )

    patient_data = {
        "demographics": {"age": 45},  # Missing sex
        # Missing labs entirely
    }

    result = await manager.prepare_data(task_plan, patient_data)

    assert result.dtmh_ready is False
    assert "demographics.sex" in result.missing_fields
    assert any("missing_labs" in flag for flag in result.data_quality_flags)


@pytest.mark.asyncio
async def test_data_manager_validates_age_range():
    """Test age range validation."""
    manager = DataManager()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 123",
        task_type="screening",
        audience="doctor",
        patient_reference="123",
        required_data=["demographics"],
        required_dtmh_capability="diabetes_screening",
    )

    patient_data = {
        "demographics": {"age": 150, "sex": "male"},  # Invalid age
    }

    result = await manager.prepare_data(task_plan, patient_data)

    assert "invalid_age_range" in result.data_quality_flags


# ============================================================================
# DTMHOrchestrator Tests
# ============================================================================


@pytest.mark.asyncio
async def test_orchestrator_creates_execution_plan_csv_mode():
    """Test DTMH execution plan creation for CSV mode."""
    orchestrator = DTMHOrchestrator()

    task_plan = ClinicalTaskPlan(
        original_query="Check patient 4",
        task_type="screening",
        audience="doctor",
        patient_reference="4",
        required_data=["demographics"],
        required_dtmh_capability="diabetes_screening",
    )

    data_result = DataPreparationResult(
        patient_id="4",
        available_modalities=["cohort_csv"],
        missing_fields=[],
        temporal_coverage={},
        dtmh_ready=True,
        payload_preview={
            "mode": "csv",
            "cohort_dir": "Dataset/private_fundus",
            "patient_id": "4",
        },
        data_quality_flags=[],
    )

    execution_plan = await orchestrator.create_execution_plan(task_plan, data_result)

    assert execution_plan.capability == "diabetes_screening"
    assert execution_plan.request_format == "dtcan_predict_csv"
    assert execution_plan.cohort_dir == "Dataset/private_fundus"
    assert execution_plan.patient_id == "4"
    assert "diabetes_probability" in execution_plan.output_heads


@pytest.mark.asyncio
async def test_orchestrator_maps_capabilities():
    """Test capability mapping for different task types."""
    orchestrator = DTMHOrchestrator()

    capability_tests = [
        ("screening", "diabetes_screening", ["diabetes_probability"]),
        ("subtyping", "subtype_classification", ["subtype_probabilities"]),
        ("complication_prediction", "complication_prediction", ["organ_risk_scores", "complication_probabilities"]),
    ]

    for task_type, expected_capability, expected_outputs in capability_tests:
        task_plan = ClinicalTaskPlan(
            original_query=f"Test {task_type}",
            task_type=task_type,
            audience="doctor",
            patient_reference="1",
            required_data=[],
            required_dtmh_capability=expected_capability,
        )

        data_result = DataPreparationResult(
            patient_id="1",
            available_modalities=["cohort_csv"],
            missing_fields=[],
            temporal_coverage={},
            dtmh_ready=True,
            payload_preview={"mode": "csv", "cohort_dir": "test", "patient_id": "1"},
            data_quality_flags=[],
        )

        execution_plan = await orchestrator.create_execution_plan(task_plan, data_result)

        assert execution_plan.capability == expected_capability
        assert execution_plan.output_heads == expected_outputs


# ============================================================================
# ClinicalInterpreter Tests
# ============================================================================


@pytest.mark.asyncio
async def test_interpreter_high_risk_screening():
    """Test interpretation of high-risk screening results."""
    interpreter = ClinicalInterpreter()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 4",
        task_type="screening",
        audience="doctor",
        patient_reference="4",
        required_data=[],
        required_dtmh_capability="diabetes_screening",
    )

    dtmh_response = {
        "patient_id": "4",
        "backend": "http",
        "summary": "High diabetes probability",
        "risk_profile": {
            "diabetes_probability": {
                "score": 0.85,
                "label": "high_probability",
            }
        },
        "recommended_next_steps": [],
        "uncertainty": {"level": "moderate"},
        "warnings": [],
    }

    interpretation = await interpreter.interpret_results(task_plan, dtmh_response)

    assert interpretation.risk_level == "high"
    assert "85.0%" in interpretation.main_conclusion
    assert "Patient 4" in interpretation.main_conclusion
    assert len(interpretation.recommended_next_actions) >= 3
    assert "HbA1c" in str(interpretation.recommended_next_actions)
    assert "ADA Standards" in interpretation.evidence_basis


@pytest.mark.asyncio
async def test_interpreter_low_risk_screening():
    """Test interpretation of low-risk screening results."""
    interpreter = ClinicalInterpreter()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 5",
        task_type="screening",
        audience="doctor",
        patient_reference="5",
        required_data=[],
        required_dtmh_capability="diabetes_screening",
    )

    dtmh_response = {
        "patient_id": "5",
        "backend": "http",
        "summary": "Low diabetes probability",
        "risk_profile": {
            "diabetes_probability": {
                "score": 0.25,
                "label": "low_probability",
            }
        },
        "recommended_next_steps": [],
        "uncertainty": {"level": "moderate"},
        "warnings": [],
    }

    interpretation = await interpreter.interpret_results(task_plan, dtmh_response)

    assert interpretation.risk_level == "low"
    assert "25.0%" in interpretation.main_conclusion
    assert "low probability" in interpretation.main_conclusion
    assert "routine monitoring" in str(interpretation.recommended_next_actions).lower()


@pytest.mark.asyncio
async def test_interpreter_critical_risk_screening():
    """Test interpretation of critical-risk screening results."""
    interpreter = ClinicalInterpreter()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 6",
        task_type="screening",
        audience="doctor",
        patient_reference="6",
        required_data=[],
        required_dtmh_capability="diabetes_screening",
    )

    dtmh_response = {
        "patient_id": "6",
        "backend": "http",
        "summary": "Very high diabetes probability",
        "risk_profile": {
            "diabetes_probability": {
                "score": 0.92,
                "label": "very_high_probability",
            }
        },
        "recommended_next_steps": [],
        "uncertainty": {"level": "moderate"},
        "warnings": [],
    }

    interpretation = await interpreter.interpret_results(task_plan, dtmh_response)

    assert interpretation.risk_level == "critical"
    assert "92.0%" in interpretation.main_conclusion
    assert "very high probability" in interpretation.main_conclusion.lower()
    assert "Immediate" in str(interpretation.recommended_next_actions)


@pytest.mark.asyncio
async def test_interpreter_extracts_data_limitations():
    """Test extraction of data limitations and warnings."""
    interpreter = ClinicalInterpreter()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 7",
        task_type="screening",
        audience="doctor",
        patient_reference="7",
        required_data=[],
        required_dtmh_capability="diabetes_screening",
    )

    dtmh_response = {
        "patient_id": "7",
        "backend": "http",
        "summary": "Screening result",
        "risk_profile": {"diabetes_probability": {"score": 0.6}},
        "recommended_next_steps": [],
        "uncertainty": {"level": "high", "note": "Sparse data"},
        "warnings": ["Missing fundus imaging", "Incomplete lab results"],
    }

    interpretation = await interpreter.interpret_results(task_plan, dtmh_response)

    assert len(interpretation.data_limitations) == 2
    assert "Missing fundus imaging" in interpretation.data_limitations
    assert interpretation.uncertainty["level"] == "high"


# ============================================================================
# WorkflowReflector Tests
# ============================================================================


@pytest.mark.asyncio
async def test_reflector_complete_workflow():
    """Test reflection on complete workflow."""
    reflector = WorkflowReflector()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 4",
        task_type="screening",
        audience="doctor",
        patient_reference="4",
        required_data=[],
        required_dtmh_capability="diabetes_screening",
    )

    interpretation = ClinicalInterpretation(
        main_conclusion="Patient 4 shows high probability of diabetes",
        risk_level="high",
        model_outputs_used={"diabetes_probability": 0.85, "probability_label": "high"},
        uncertainty={"level": "moderate"},
        data_limitations=[],
        recommended_next_actions=["Order HbA1c", "Schedule follow-up"],
        evidence_basis=["ADA Standards", "DTMH model"],
    )

    decision = await reflector.reflect(task_plan, interpretation)

    assert decision.is_complete is True
    assert decision.next_action == "finalize"
    assert "screening completed" in decision.reason.lower()
    assert len(decision.failure_modes) == 0
    assert len(decision.additional_queries) == 0


@pytest.mark.asyncio
async def test_reflector_detects_insufficient_data():
    """Test detection of insufficient data failure mode."""
    reflector = WorkflowReflector()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 4",
        task_type="screening",
        audience="doctor",
        patient_reference="4",
        required_data=[],
        required_dtmh_capability="diabetes_screening",
    )

    interpretation = ClinicalInterpretation(
        main_conclusion="Incomplete analysis",
        risk_level="unknown",
        model_outputs_used={},
        uncertainty={"level": "high"},
        data_limitations=["missing_critical_field_demographics.age"],
        recommended_next_actions=[],
        evidence_basis=["ADA Standards"],
    )

    decision = await reflector.reflect(task_plan, interpretation)

    assert decision.is_complete is False
    assert "insufficient_data" in decision.failure_modes
    assert decision.next_action == "fetch_data"
    assert len(decision.additional_queries) > 0
    assert "missing patient data" in decision.additional_queries[0].lower()


@pytest.mark.asyncio
async def test_reflector_detects_model_uncertainty():
    """Test detection of model uncertainty failure mode."""
    reflector = WorkflowReflector()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 4",
        task_type="screening",
        audience="doctor",
        patient_reference="4",
        required_data=[],
        required_dtmh_capability="diabetes_screening",
    )

    interpretation = ClinicalInterpretation(
        main_conclusion="Uncertain result",
        risk_level="unknown",
        model_outputs_used={"diabetes_probability": 0.5},
        uncertainty={"level": "very_high", "note": "Conflicting signals"},
        data_limitations=[],
        recommended_next_actions=["Review data quality"],
        evidence_basis=["ADA Standards"],
    )

    decision = await reflector.reflect(task_plan, interpretation)

    assert decision.is_complete is False
    assert "model_uncertainty" in decision.failure_modes
    assert decision.next_action == "retrieve_evidence"


@pytest.mark.asyncio
async def test_reflector_detects_data_quality_issues():
    """Test detection of data quality issues."""
    reflector = WorkflowReflector()

    task_plan = ClinicalTaskPlan(
        original_query="Screen patient 4",
        task_type="screening",
        audience="doctor",
        patient_reference="4",
        required_data=[],
        required_dtmh_capability="diabetes_screening",
    )

    interpretation = ClinicalInterpretation(
        main_conclusion="Analysis with quality concerns",
        risk_level="moderate",
        model_outputs_used={"diabetes_probability": 0.6},
        uncertainty={"level": "moderate"},
        data_limitations=["invalid_age_format", "sparse_data"],
        recommended_next_actions=["Validate data", "Rerun analysis"],
        evidence_basis=["ADA Standards"],
    )

    decision = await reflector.reflect(task_plan, interpretation)

    assert decision.is_complete is False
    assert "data_quality_issues" in decision.failure_modes
    assert decision.next_action == "validate_data"


@pytest.mark.asyncio
async def test_reflector_generates_task_specific_reasons():
    """Test task-specific completion reasons."""
    reflector = WorkflowReflector()

    task_types = [
        ("screening", "screening completed"),
        ("risk_assessment", "risk assessment completed"),
        ("complication_prediction", "complication prediction completed"),
    ]

    for task_type, expected_phrase in task_types:
        task_plan = ClinicalTaskPlan(
            original_query=f"Test {task_type}",
            task_type=task_type,
            audience="doctor",
            patient_reference="1",
            required_data=[],
            required_dtmh_capability="test",
        )

        interpretation = ClinicalInterpretation(
            main_conclusion="Complete",
            risk_level="moderate",
            model_outputs_used={"score": 0.5, "label": "moderate"},
            uncertainty={"level": "moderate"},
            data_limitations=[],
            recommended_next_actions=["Follow up"],
            evidence_basis=["Guidelines"],
        )

        decision = await reflector.reflect(task_plan, interpretation)

        assert decision.is_complete is True
        assert expected_phrase in decision.reason.lower()
