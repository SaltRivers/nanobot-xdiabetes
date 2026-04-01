"""HTTP adapter for external DTMH services."""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from xdiabetes.clinical.adapters.base import DTMHAdapter
from xdiabetes.clinical.errors import DTMHAdapterError
from xdiabetes.clinical.schemas import DTMHRequest, DTMHResult, PatientCase
from xdiabetes.config.schema import XDiabetesDTMHConfig


def _truncate_json(data: Any, max_len: int = 1000) -> str:
    """Serialize data to JSON string, truncating if too long."""
    try:
        s = _json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        s = str(data)
    if len(s) > max_len:
        return s[:max_len] + "...(truncated)"
    return s


class HTTPDTMHAdapter(DTMHAdapter):
    """Call a remote DTMH service over HTTP.

    Three request styles are supported:

    - ``xdiabetes``: POST the native ``DTMHRequest`` to a service that already
      returns ``DTMHResult``-compatible JSON (legacy behavior).
    - ``dtcan_predict``: POST to the DT-CAN-style ``/predict`` API. This adapter
      translates the X-Diabetes ``PatientCase`` into the raw EHR/text payload
      expected by that service and normalizes the response into ``DTMHResult``.
    - ``dtcan_predict_csv``: POST ``cohort_dir`` + ``patient_id`` directly to
      the ``/predict_csv`` endpoint. The DTMH model runs on a remote server;
      no local deep-learning libraries are needed.
    """

    def __init__(self, config: XDiabetesDTMHConfig):
        self._base_url = config.http_base_url.rstrip("/")
        self._timeout_s = config.timeout_s
        self._endpoint = self._normalize_endpoint(config.http_endpoint)
        self._request_format = config.http_request_format
        self._headers = dict(config.headers)
        self._checkpoint_path = config.checkpoint_path
        self._config_path = config.config_path
        self._encode_raw = config.encode_raw
        self._output_format = config.output_format
        self._return_latents = config.return_latents
        self._threshold = config.threshold
        self._organ_filter = list(config.organ_filter)
        if not self._base_url:
            raise DTMHAdapterError("httpBaseUrl is required when dtmh.backend='http'.")

    @property
    def backend_name(self) -> str:
        return "http"

    def analyze(self, request: DTMHRequest) -> DTMHResult:
        endpoint = f"{self._base_url}{self._endpoint}"
        request_payload = self._build_request_payload(request)

        logger.debug(
            "DTMH HTTP request: POST {} payload_keys={} format={}",
            endpoint,
            sorted(request_payload.keys()),
            self._request_format,
        )
        logger.debug("DTMH HTTP payload: {}", _truncate_json(request_payload))

        try:
            response = httpx.post(
                endpoint,
                json=request_payload,
                headers=self._headers or None,
                timeout=self._timeout_s,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - depends on external service
            logger.debug("DTMH HTTP request failed: {}", exc)
            raise DTMHAdapterError(f"HTTP DTMH request failed: {exc}") from exc

        logger.debug(
            "DTMH HTTP response: status={} content_length={}",
            response.status_code,
            len(response.content),
        )

        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - depends on external service
            logger.debug(
                "DTMH HTTP response was not valid JSON: {}",
                response.text[:300],
            )
            raise DTMHAdapterError("HTTP DTMH response was not valid JSON.") from exc

        logger.debug("DTMH HTTP response body: {}", _truncate_json(payload))
        return self._normalize_response(request, request_payload, payload)

    def _build_request_payload(self, request: DTMHRequest) -> dict[str, Any]:
        if self._request_format == "xdiabetes":
            return request.model_dump(mode="json")
        if self._request_format == "dtcan_predict":
            return self._build_dtcan_predict_payload(request)
        if self._request_format == "dtcan_predict_csv":
            return self._build_dtcan_predict_csv_payload(request)
        raise DTMHAdapterError(
            f"Unsupported dtmh.httpRequestFormat='{self._request_format}'. "
            "Use 'xdiabetes', 'dtcan_predict', or 'dtcan_predict_csv'."
        )

    def _build_dtcan_predict_payload(self, request: DTMHRequest) -> dict[str, Any]:
        if not self._checkpoint_path:
            raise DTMHAdapterError(
                "checkpointPath is required when dtmh.httpRequestFormat='dtcan_predict'."
            )

        overrides = self._extract_case_dtmh_overrides(request.patient)
        data_override = overrides.get("data")
        config_override = overrides.get("config")
        request_override = overrides.get("request_body") or overrides.get("requestBody")
        modalities_override = overrides.get("modalities") or overrides.get("modalities_only")
        omit_modalities = overrides.get("omit_modalities") or overrides.get("omitModalities")

        if data_override is not None and not isinstance(data_override, dict):
            raise DTMHAdapterError("patient.metadata.dtmh.data must be a JSON object when provided.")
        if config_override is not None and not isinstance(config_override, dict):
            raise DTMHAdapterError("patient.metadata.dtmh.config must be a JSON object when provided.")
        if request_override is not None and not isinstance(request_override, dict):
            raise DTMHAdapterError(
                "patient.metadata.dtmh.requestBody must be a JSON object when provided."
            )
        if modalities_override is not None and not isinstance(modalities_override, list):
            raise DTMHAdapterError("patient.metadata.dtmh.modalities must be a JSON array when provided.")
        if omit_modalities is not None and not isinstance(omit_modalities, list):
            raise DTMHAdapterError("patient.metadata.dtmh.omit_modalities must be a JSON array when provided.")

        data = data_override if isinstance(data_override, dict) else self._patient_case_to_dtcan_data(request.patient)
        if isinstance(modalities_override, list):
            allowed = {str(item) for item in modalities_override}
            data = {key: value for key, value in data.items() if key in allowed}
        if isinstance(omit_modalities, list):
            blocked = {str(item) for item in omit_modalities}
            data = {key: value for key, value in data.items() if key not in blocked}
        config: dict[str, Any] = {
            "encode_raw": self._encode_raw,
            "output_format": self._output_format,
            "return_latents": self._return_latents,
        }
        if self._config_path:
            config["config_path"] = self._config_path
        if self._output_format == "binary":
            config["threshold"] = self._threshold
        if self._organ_filter:
            config["organ_filter"] = self._organ_filter
        if isinstance(config_override, dict):
            config = self._merge_dicts(config, config_override)

        body: dict[str, Any] = {
            "checkpoint_path": self._checkpoint_path,
            "data": data,
            "config": config,
        }
        if isinstance(request_override, dict):
            body = self._merge_dicts(body, request_override)
        return body

    def _build_dtcan_predict_csv_payload(self, request: DTMHRequest) -> dict[str, Any]:
        """Build the payload for the /predict_csv endpoint.

        This mode sends cohort_dir + patient_id directly to the remote DTMH
        HTTP service. The model runs server-side; no local deep-learning
        libraries are needed.

        Expected request body::

            {
                "cohort_dir": "Dataset/private_fundus",
                "patient_id": 4,
                "checkpoint_path": "checkpoints/deepdr_ehr_text/best.pt",
                "config_path": "src/configs/deepdr_ehr_text.yaml",
                "output_format": "probabilities"
            }
        """
        # Extract cohort_dir and patient_id from the request's extra fields
        # or from the patient case metadata.
        cohort_dir = getattr(request, "cohort_dir", None)
        patient_id_raw = getattr(request, "patient_id_csv", None)
        if cohort_dir is None and isinstance(request.patient.metadata, dict):
            cohort_dir = request.patient.metadata.get("cohort_dir")
        if patient_id_raw is None and isinstance(request.patient.metadata, dict):
            patient_id_raw = request.patient.metadata.get("patient_id_csv")
        # Fallback: use patient_id from the patient case directly
        if patient_id_raw is None:
            raw_id = request.patient.patient_id
            # Convert to int if the ID is numeric (the /predict_csv endpoint expects int)
            try:
                patient_id_raw = int(raw_id)
            except (TypeError, ValueError):
                patient_id_raw = raw_id

        if not cohort_dir:
            raise DTMHAdapterError(
                "cohort_dir is required for dtcan_predict_csv format. "
                "Set it in the request metadata or as a tool parameter."
            )

        body: dict[str, Any] = {
            "cohort_dir": cohort_dir,
            "patient_id": patient_id_raw,
        }
        if self._checkpoint_path:
            body["checkpoint_path"] = self._checkpoint_path
        if self._config_path:
            body["config_path"] = self._config_path
        if self._output_format:
            body["output_format"] = self._output_format
        return body

    def _normalize_response(
        self,
        request: DTMHRequest,
        request_payload: dict[str, Any],
        payload: Any,
    ) -> DTMHResult:
        if not isinstance(payload, dict):
            raise DTMHAdapterError("HTTP DTMH response must be a JSON object.")

        if self._looks_like_native_dtmh_result(payload):
            try:
                return DTMHResult.model_validate(payload)
            except Exception as exc:
                raise DTMHAdapterError(f"HTTP DTMH response could not be validated: {exc}") from exc

        if self._request_format == "dtcan_predict" or "predictions" in payload:
            return self._normalize_dtcan_predict_response(
                request=request,
                request_payload=request_payload,
                payload=payload,
            )

        if self._request_format == "dtcan_predict_csv":
            return self._normalize_dtcan_predict_response(
                request=request,
                request_payload=request_payload,
                payload=payload,
            )

        if any(key in payload for key in ("diabetes_probability", "diabetesProbability", "probability")):
            return self._normalize_diabetes_probability_response(
                request=request,
                request_payload=request_payload,
                payload=payload,
            )

        raise DTMHAdapterError(
            "HTTP DTMH response was neither a DTMHResult payload nor a recognized DT-CAN prediction payload."
        )

    def _normalize_dtcan_predict_response(
        self,
        *,
        request: DTMHRequest,
        request_payload: dict[str, Any],
        payload: dict[str, Any],
    ) -> DTMHResult:
        predictions = payload.get("predictions")
        metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
        system_predictions = self._extract_system_predictions(payload)
        diabetes_probability = self._extract_diabetes_probability(payload)
        if diabetes_probability is None:
            raise DTMHAdapterError(
                "The configured DTMH HTTP response did not expose a diabetes probability."
            )

        organ_states = self._extract_organ_states(predictions)
        probability_label = self._probability_label(diabetes_probability)
        summary = (
            f"HTTP DTMH backend estimated diabetes probability {diabetes_probability:.3f} "
            f"({probability_label})."
        )
        warnings = []
        if not organ_states:
            warnings.append(
                "Current DTMH HTTP integration only exposes structured diabetes probability; "
                "organ-state outputs were not returned by the remote service."
            )

        next_steps = [
            "Validate the model probability against labs, history, and clinician review.",
        ]
        if diabetes_probability >= 0.5:
            next_steps.append("Review glycemic markers and confirmatory diabetes work-up if clinically appropriate.")
        else:
            next_steps.append("If suspicion remains high, correlate with HbA1c, fasting glucose, and follow-up data.")

        uncertainty: dict[str, Any] = {
            "level": "unknown",
            "note": "The current integration is aligned primarily around diabetes probability.",
        }
        if metadata:
            uncertainty["source_metadata"] = metadata

        model_version = self._derive_model_version(metadata)
        risk_profile: dict[str, Any] = {
            "diabetes_probability": {
                "label": probability_label,
                "score": diabetes_probability,
            },
        }
        if system_predictions:
            risk_profile["system_probabilities"] = system_predictions

        return DTMHResult(
            patient_id=request.patient.patient_id,
            backend=self.backend_name,
            summary=summary,
            model_version=model_version,
            organ_states=organ_states,
            risk_profile=risk_profile,
            recommended_next_steps=next_steps,
            uncertainty=uncertainty,
            warnings=warnings,
            source_predictions=predictions if isinstance(predictions, dict) else {},
            source_metadata=metadata,
            request_format=self._request_format,
            request_endpoint=self._endpoint,
            request_payload_preview=self._summarize_request_payload(request_payload),
        )

    def _normalize_diabetes_probability_response(
        self,
        *,
        request: DTMHRequest,
        request_payload: dict[str, Any],
        payload: dict[str, Any],
    ) -> DTMHResult:
        diabetes_probability = self._extract_diabetes_probability(payload)
        if diabetes_probability is None:
            raise DTMHAdapterError(
                "Could not extract diabetes probability from the configured DTMH HTTP response."
            )

        probability_label = self._probability_label(diabetes_probability)
        return DTMHResult(
            patient_id=request.patient.patient_id,
            backend=self.backend_name,
            summary=(
                f"HTTP DTMH backend estimated diabetes probability {diabetes_probability:.3f} "
                f"({probability_label})."
            ),
            model_version="http-dtmh",
            risk_profile={
                "diabetes_probability": {
                    "label": probability_label,
                    "score": diabetes_probability,
                }
            },
            recommended_next_steps=[
                "Validate the model probability against the patient context and structured labs."
            ],
            uncertainty={
                "level": "unknown",
                "note": "The current remote DTMH response only exposes diabetes probability.",
            },
            warnings=[
                "The current DTMH HTTP response exposes only diabetes probability; richer structured outputs can be added later."
            ],
            source_response=payload,
            request_format=self._request_format,
            request_endpoint=self._endpoint,
            request_payload_preview=self._summarize_request_payload(request_payload),
        )

    def _patient_case_to_dtcan_data(self, patient: PatientCase) -> dict[str, Any]:
        demographics = patient.demographics
        vitals = patient.vitals
        labs = patient.labs
        history = patient.history
        imaging = patient.imaging

        ehr = [
            float(self._map_gender(demographics.get("sex") or demographics.get("gender"))),
            self._as_float(demographics.get("age"), default=0.0),
            self._as_float(demographics.get("height_cm") or demographics.get("height"), default=0.0),
            self._as_float(demographics.get("weight_kg") or demographics.get("weight"), default=0.0),
            self._as_float(demographics.get("bmi"), default=0.0),
            self._as_float(vitals.get("sbp"), default=0.0),
            self._as_float(vitals.get("dbp"), default=0.0),
            self._as_float(labs.get("triglycerides_mmol_l") or labs.get("triglyceride"), default=0.0),
            self._as_float(labs.get("hdl_mmol_l") or labs.get("hdl"), default=0.0),
            self._as_float(labs.get("ldl_mmol_l") or labs.get("ldl"), default=0.0),
            self._as_float(labs.get("hba1c") or labs.get("HbA1c"), default=0.0),
            self._as_float(
                history.get("duration_years")
                or history.get("diabetes_duration_years")
                or history.get("years_since_diagnosis"),
                default=0.0,
            ),
            float(self._map_smoke(history)),
        ]

        data: dict[str, Any] = {"ehr": ehr}
        text = self._build_text_entries(patient, imaging=imaging, history=history)
        if text:
            data["text"] = text
        return data

    def _build_text_entries(
        self,
        patient: PatientCase,
        *,
        imaging: dict[str, Any],
        history: dict[str, Any],
    ) -> list[str]:
        entries: list[str] = []

        if patient.notes:
            entries.append(str(patient.notes))

        fundus_summary = imaging.get("fundus_summary")
        if fundus_summary:
            entries.append(f"Fundus summary: {fundus_summary}")

        complications = patient.complications
        if isinstance(complications, list) and complications:
            entries.append("Complications: " + ", ".join(str(item) for item in complications))
        elif isinstance(complications, dict) and complications:
            entries.append("Complications: " + ", ".join(f"{k}={v}" for k, v in complications.items()))

        medications = patient.medications
        if medications:
            med_lines = []
            for item in medications:
                if isinstance(item, dict):
                    name = item.get("name", "unknown")
                    dose = item.get("dose", "")
                    med_lines.append(" ".join(part for part in [str(name), str(dose)] if part).strip())
                else:
                    med_lines.append(str(item))
            entries.append("Medications: " + "; ".join(item for item in med_lines if item))

        history_bits = []
        for key in (
            "family_history_diabetes",
            "stroke_history",
            "smoking",
            "smoker",
            "smoking_status",
        ):
            if key in history and history[key] not in ("", None):
                history_bits.append(f"{key}={history[key]}")
        if history_bits:
            entries.append("History: " + "; ".join(history_bits))

        return [entry for entry in entries if entry.strip()]

    def _extract_organ_states(self, predictions: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(predictions, dict):
            return {}

        organ_states: dict[str, dict[str, Any]] = {}
        for key, value in predictions.items():
            if not key.startswith("organ/") or not isinstance(value, dict):
                continue
            organ_name = key.split("/", 1)[1]
            score = self._extract_diabetes_probability(value)
            if score is None:
                numeric_values = [self._as_float(item) for item in value.values()]
                numeric_values = [item for item in numeric_values if item is not None]
                score = max(numeric_values) if numeric_values else None
            organ_states[organ_name] = {
                "state": self._probability_label(score) if score is not None else "unknown",
                "score": score if score is not None else "n/a",
                "probabilities": value,
            }
        return organ_states

    def _extract_system_predictions(self, payload: dict[str, Any]) -> dict[str, float]:
        predictions = payload.get("predictions")
        if isinstance(predictions, dict):
            if isinstance(predictions.get("system"), dict):
                return self._floatify_mapping(predictions["system"])
            if all(not isinstance(value, dict) for value in predictions.values()):
                return self._floatify_mapping(predictions)

        system = payload.get("system")
        if isinstance(system, dict):
            return self._floatify_mapping(system)

        probability = self._extract_diabetes_probability(payload)
        if probability is not None:
            return {"diabetes": probability}
        return {}

    def _extract_diabetes_probability(self, payload: Any) -> float | None:
        candidates = [
            self._get_path(payload, "predictions", "system", "diabetes"),
            self._get_path(payload, "predictions", "diabetes"),
            self._get_path(payload, "system", "diabetes"),
            self._get_path(payload, "risk_profile", "diabetes_probability", "score"),
            self._get_path(payload, "diabetes_probability"),
            self._get_path(payload, "diabetesProbability"),
            self._get_path(payload, "probability"),
        ]
        for candidate in candidates:
            value = self._as_float(candidate)
            if value is not None:
                return value

        if isinstance(payload, dict):
            for key, value in payload.items():
                if key.lower() == "diabetes":
                    numeric = self._as_float(value)
                    if numeric is not None:
                        return numeric
                if isinstance(value, dict):
                    nested = self._extract_diabetes_probability(value)
                    if nested is not None:
                        return nested
        return None

    def _derive_model_version(self, metadata: dict[str, Any]) -> str:
        for key in ("model_version", "modelVersion", "checkpoint_name", "checkpointName"):
            value = metadata.get(key)
            if value:
                return str(value)
        checkpoint_path = metadata.get("checkpoint_path") or metadata.get("checkpointPath") or self._checkpoint_path
        if checkpoint_path:
            return Path(str(checkpoint_path)).name
        return "http-dtmh"

    def _extract_case_dtmh_overrides(self, patient: PatientCase) -> dict[str, Any]:
        metadata = patient.metadata if isinstance(patient.metadata, dict) else {}
        for key in ("dtmh", "dtmh_input", "dtmhInput", "dtcan", "dtcan_input", "dtcanInput"):
            value = metadata.get(key)
            if isinstance(value, dict):
                if any(name in value for name in ("data", "config", "request_body", "requestBody")):
                    return value
                if any(name in value for name in ("ehr", "text", "image")):
                    return {"data": value}
                return value
        return {}

    def _summarize_request_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        summary = {"keys": sorted(payload.keys())}
        if self._request_format == "dtcan_predict":
            data = payload.get("data", {})
            config = payload.get("config", {})
            if isinstance(data, dict):
                summary["data_modalities"] = sorted(data.keys())
            if isinstance(config, dict):
                summary["config_keys"] = sorted(config.keys())
        elif self._request_format == "dtcan_predict_csv":
            if "cohort_dir" in payload:
                summary["cohort_dir"] = payload["cohort_dir"]
            if "patient_id" in payload:
                summary["patient_id"] = payload["patient_id"]
        return summary

    @staticmethod
    def _looks_like_native_dtmh_result(payload: dict[str, Any]) -> bool:
        required = {"patient_id", "backend", "summary"}
        return required.issubset(payload.keys())

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        cleaned = (endpoint or "/analyze").strip()
        return cleaned if cleaned.startswith("/") else f"/{cleaned}"

    @staticmethod
    def _merge_dicts(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in extra.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = HTTPDTMHAdapter._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _map_gender(value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(float(value) != 0.0)
        text = str(value or "").strip().lower()
        if text in {"male", "man", "m", "男", "1"}:
            return 1
        if text in {"female", "woman", "f", "女", "0"}:
            return 0
        return 0

    @staticmethod
    def _map_smoke(history: dict[str, Any]) -> int:
        for key in ("smoke", "smoking", "smoker", "smoking_history", "smoking_status"):
            if key not in history:
                continue
            value = history.get(key)
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float)):
                return int(float(value) != 0.0)
            text = str(value or "").strip().lower()
            if text in {"yes", "true", "current", "former", "smoker", "1"}:
                return 1
            if text in {"no", "false", "never", "non-smoker", "0"}:
                return 0
        return 0

    @staticmethod
    def _floatify_mapping(mapping: dict[str, Any]) -> dict[str, float]:
        result: dict[str, float] = {}
        for key, value in mapping.items():
            numeric = HTTPDTMHAdapter._as_float(value)
            if numeric is not None:
                result[key] = numeric
        return result

    @staticmethod
    def _as_float(value: Any, default: float | None = None) -> float | None:
        if value in ("", None):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_path(payload: Any, *keys: str) -> Any:
        current = payload
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    @staticmethod
    def _probability_label(score: float | None) -> str:
        if score is None:
            return "unknown"
        if score >= 0.8:
            return "very_high_probability"
        if score >= 0.6:
            return "high_probability"
        if score >= 0.4:
            return "intermediate_probability"
        return "low_probability"
