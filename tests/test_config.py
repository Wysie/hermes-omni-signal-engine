import json

from hermes_omni_signal_engine.config import default_config, load_config, normalize


def test_normalize_defaults_enable_visible_distillation_but_not_command_execution():
    cfg = normalize({})
    assert cfg.enabled is True
    assert cfg.enable_omni_cmd is False
    assert cfg.enable_transform_terminal_output is True
    assert "LD_PRELOAD" in cfg.dangerous_env_vars


def test_normalize_accepts_legacy_omni_path_key():
    cfg = normalize({"omniPath": "/usr/local/bin/omni", "enable_omni_cmd": "true"})
    assert cfg.omni_path == "/usr/local/bin/omni"
    assert cfg.enable_omni_cmd is True
