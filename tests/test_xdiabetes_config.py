from xdiabetes.config.schema import Config


def test_xdiabetes_config_accepts_camel_case_aliases():
    config = Config.model_validate(
        {
            "xDiabetes": {
                "enabled": True,
                "mode": "patient",
                "workspace": "~/xdiabetes-test",
                "dtmh": {
                    "backend": "http",
                    "httpBaseUrl": "http://127.0.0.1:8000",
                    "httpEndpoint": "/predict",
                    "httpRequestFormat": "dtcan_predict",
                    "checkpointPath": "/tmp/model.pt",
                    "configPath": "/tmp/config.yaml",
                    "encodeRaw": True,
                    "outputFormat": "probabilities",
                    "returnLatents": False,
                    "headers": {"Authorization": "Bearer test"},
                },
                "memory": {"patientMemoryDir": "patient_memory"},
                "rag": {"backend": "api", "apiBaseUrl": "http://127.0.0.1:8008"},
                "learning": {
                    "enabled": True,
                    "strictPrivacy": True,
                    "requireHumanApproval": True,
                    "autoActivate": False,
                    "learningDir": "learning",
                },
            }
        }
    )

    assert config.clinical.enabled is True
    assert config.clinical.mode == "patient"
    assert config.clinical.workspace == "~/xdiabetes-test"
    assert config.clinical.dtmh.backend == "http"
    assert config.clinical.dtmh.http_base_url == "http://127.0.0.1:8000"
    assert config.clinical.dtmh.http_endpoint == "/predict"
    assert config.clinical.dtmh.http_request_format == "dtcan_predict"
    assert config.clinical.dtmh.checkpoint_path == "/tmp/model.pt"
    assert config.clinical.dtmh.config_path == "/tmp/config.yaml"
    assert config.clinical.dtmh.encode_raw is True
    assert config.clinical.dtmh.output_format == "probabilities"
    assert config.clinical.dtmh.return_latents is False
    assert config.clinical.dtmh.headers == {"Authorization": "Bearer test"}
    assert config.clinical.memory.patient_memory_dir == "patient_memory"
    assert config.clinical.rag.backend == "api"
    assert config.clinical.rag.api_base_url == "http://127.0.0.1:8008"
    assert config.clinical.learning.enabled is True
    assert config.clinical.learning.strict_privacy is True
    assert config.clinical.learning.require_human_approval is True
    assert config.clinical.learning.auto_activate is False
    assert config.clinical.learning.learning_dir == "learning"
