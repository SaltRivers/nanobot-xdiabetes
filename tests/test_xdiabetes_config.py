from xdiabetes.config.schema import Config


def test_xdiabetes_config_accepts_camel_case_aliases():
    config = Config.model_validate(
        {
            "xDiabetes": {
                "enabled": True,
                "mode": "patient",
                "workspace": "~/xdiabetes-test",
                "dtmh": {"backend": "mock"},
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
    assert config.clinical.dtmh.backend == "mock"
    assert config.clinical.memory.patient_memory_dir == "patient_memory"
    assert config.clinical.rag.backend == "api"
    assert config.clinical.rag.api_base_url == "http://127.0.0.1:8008"
    assert config.clinical.learning.enabled is True
    assert config.clinical.learning.strict_privacy is True
    assert config.clinical.learning.require_human_approval is True
    assert config.clinical.learning.auto_activate is False
    assert config.clinical.learning.learning_dir == "learning"
