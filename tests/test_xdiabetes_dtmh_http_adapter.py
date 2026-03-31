from __future__ import annotations

from typing import Any

import pytest

from xdiabetes.clinical.adapters.http import HTTPDTMHAdapter
from xdiabetes.clinical.schemas import DTMHRequest, PatientCase
from xdiabetes.config.schema import XDiabetesDTMHConfig


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def _demo_request(**patient_overrides: Any) -> DTMHRequest:
    patient = PatientCase(
        patient_id="demo_patient",
        demographics={"age": 46, "sex": "female", "bmi": 29.4},
        vitals={"sbp": 148, "dbp": 92},
        labs={"hba1c": 8.7, "ldl_mmol_l": 3.2, "triglycerides_mmol_l": 2.1},
        history={"duration_years": 4, "smoke": False},
        imaging={"fundus_summary": "Mild diabetic retinopathy suspected."},
        notes="Demo note for DTMH integration.",
        **patient_overrides,
    )
    return DTMHRequest(patient=patient, task="general", clinical_question="Assess diabetes risk")


def test_http_dtmh_adapter_maps_dtcan_predict_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, *, json: dict[str, Any], headers: dict[str, str] | None, timeout: int):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeResponse(
            {
                "predictions": {
                    "system": {
                        "diabetes": 0.78,
                        "mi": 0.12,
                    }
                },
                "metadata": {
                    "model_version": "dtmh-v1",
                    "inference_time_ms": 123.4,
                },
            }
        )

    monkeypatch.setattr("xdiabetes.clinical.adapters.http.httpx.post", fake_post)

    adapter = HTTPDTMHAdapter(
        XDiabetesDTMHConfig(
            backend="http",
            http_base_url="http://127.0.0.1:8000",
            http_endpoint="/predict",
            http_request_format="dtcan_predict",
            checkpoint_path="/models/dtmh.pt",
            config_path="/models/dtmh.yaml",
            encode_raw=True,
            output_format="probabilities",
            headers={"Authorization": "Bearer test"},
        )
    )

    result = adapter.analyze(_demo_request())

    assert captured["url"] == "http://127.0.0.1:8000/predict"
    assert captured["headers"] == {"Authorization": "Bearer test"}
    assert captured["timeout"] == 30
    assert captured["json"]["checkpoint_path"] == "/models/dtmh.pt"
    assert captured["json"]["config"]["config_path"] == "/models/dtmh.yaml"
    assert captured["json"]["config"]["encode_raw"] is True
    assert captured["json"]["data"]["ehr"] == [0.0, 46.0, 0.0, 0.0, 29.4, 148.0, 92.0, 2.1, 0.0, 3.2, 8.7, 4.0, 0.0]
    assert "text" in captured["json"]["data"]

    assert result.patient_id == "demo_patient"
    assert result.backend == "http"
    assert result.model_version == "dtmh-v1"
    assert result.risk_profile["diabetes_probability"]["score"] == pytest.approx(0.78)
    assert result.risk_profile["system_probabilities"]["mi"] == pytest.approx(0.12)
    assert "0.780" in result.summary


def test_http_dtmh_adapter_honors_patient_level_dtmh_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, *, json: dict[str, Any], headers: dict[str, str] | None, timeout: int):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse({"diabetes_probability": 0.91})

    monkeypatch.setattr("xdiabetes.clinical.adapters.http.httpx.post", fake_post)

    adapter = HTTPDTMHAdapter(
        XDiabetesDTMHConfig(
            backend="http",
            http_base_url="http://127.0.0.1:8000",
            http_endpoint="/predict",
            http_request_format="dtcan_predict",
            checkpoint_path="/models/dtmh.pt",
            encode_raw=True,
        )
    )

    request = _demo_request(
        metadata={
            "dtmh": {
                "data": {"ehr": [1, 2, 3], "text": ["override text"]},
                "config": {"encode_raw": False},
            }
        }
    )

    result = adapter.analyze(request)

    assert captured["json"]["data"] == {"ehr": [1, 2, 3], "text": ["override text"]}
    assert captured["json"]["config"]["encode_raw"] is False
    assert result.risk_profile["diabetes_probability"]["score"] == pytest.approx(0.91)
    assert "0.910" in result.summary


def test_http_dtmh_adapter_supports_modalities_filter_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, *, json: dict[str, Any], headers: dict[str, str] | None, timeout: int):
        captured["json"] = json
        return _FakeResponse({"diabetes_probability": 0.61})

    monkeypatch.setattr("xdiabetes.clinical.adapters.http.httpx.post", fake_post)

    adapter = HTTPDTMHAdapter(
        XDiabetesDTMHConfig(
            backend="http",
            http_base_url="http://127.0.0.1:8000",
            http_endpoint="/predict",
            http_request_format="dtcan_predict",
            checkpoint_path="/models/dtmh.pt",
            encode_raw=True,
        )
    )

    request = _demo_request(
        metadata={
            "dtmh": {
                "modalities": ["ehr"],
            }
        }
    )

    adapter.analyze(request)

    assert set(captured["json"]["data"].keys()) == {"ehr"}
