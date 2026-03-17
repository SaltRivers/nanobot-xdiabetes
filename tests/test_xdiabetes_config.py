from nanobot.config.schema import Config


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
            }
        }
    )

    assert config.x_diabetes.enabled is True
    assert config.x_diabetes.mode == "patient"
    assert config.x_diabetes.workspace == "~/xdiabetes-test"
    assert config.x_diabetes.dtmh.backend == "mock"
    assert config.x_diabetes.memory.patient_memory_dir == "patient_memory"
    assert config.x_diabetes.rag.backend == "api"
    assert config.x_diabetes.rag.api_base_url == "http://127.0.0.1:8008"
