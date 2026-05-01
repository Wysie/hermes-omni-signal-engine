from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PLUGIN_NAME = "hermes-omni-plugin"
LEGACY_PLUGIN_NAME = "omni-signal-engine"

DEFAULT_DANGEROUS_ENV_VARS = [
    "BASH_ENV",
    "ENV",
    "ZDOTDIR",
    "BASH_PROFILE",
    "PROMPT_COMMAND",
    "IFS",
    "NODE_OPTIONS",
    "PYTHONSTARTUP",
    "PYTHONINSPECT",
    "PYTHONPATH",
    "PYTHONHOME",
    "RUBYOPT",
    "RUBYLIB",
    "JAVA_TOOL_OPTIONS",
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_FORCE_FLAT_NAMESPACE",
    "GIT_ASKPASS",
    "GIT_EXEC_PATH",
    "GIT_TEMPLATE_DIR",
    "SSH_ASKPASS",
]


@dataclass
class PluginConfig:
    enabled: bool = True
    omni_path: str = "omni"
    timeout_seconds: int = 120
    sanitize_env: bool = True
    dangerous_env_vars: list[str] = field(default_factory=lambda: list(DEFAULT_DANGEROUS_ENV_VARS))
    # Visible by default: users who install and enable the plugin should immediately see
    # OMNI distill noisy terminal output. The terminal-equivalent command runner remains opt-in.
    enable_transform_terminal_output: bool = True
    # Command execution is intentionally opt-in because it is terminal-equivalent and may have side effects.
    enable_omni_cmd: bool = False
    max_input_chars: int = 1_000_000
    max_output_chars: int = 80_000
    include_stderr_in_distillation: bool = True
    preserve_raw_on_omni_failure: bool = True


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def plugin_data_dir() -> Path:
    path = hermes_home() / "plugin-data" / PLUGIN_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def legacy_config_path() -> Path:
    return hermes_home() / "plugin-data" / LEGACY_PLUGIN_NAME / "config.json"


def config_path() -> Path:
    return plugin_data_dir() / "config.json"


def default_config() -> PluginConfig:
    return PluginConfig()


def _bool(data: dict[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _int(data: dict[str, Any], key: str, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        value = int(data.get(key, default))
    except Exception:
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def normalize(data: dict[str, Any]) -> PluginConfig:
    cfg = PluginConfig(
        enabled=_bool(data, "enabled", True),
        omni_path=str(data.get("omni_path") or data.get("omniPath") or "omni"),
        timeout_seconds=_int(data, "timeout_seconds", 120, minimum=1, maximum=3600),
        sanitize_env=_bool(data, "sanitize_env", True),
        dangerous_env_vars=list(data.get("dangerous_env_vars") or DEFAULT_DANGEROUS_ENV_VARS),
        enable_transform_terminal_output=_bool(data, "enable_transform_terminal_output", True),
        enable_omni_cmd=_bool(data, "enable_omni_cmd", False),
        max_input_chars=_int(data, "max_input_chars", 1_000_000, minimum=1000, maximum=20_000_000),
        max_output_chars=_int(data, "max_output_chars", 80_000, minimum=1000, maximum=2_000_000),
        include_stderr_in_distillation=_bool(data, "include_stderr_in_distillation", True),
        preserve_raw_on_omni_failure=_bool(data, "preserve_raw_on_omni_failure", True),
    )
    cfg.dangerous_env_vars = [str(v) for v in cfg.dangerous_env_vars if str(v).strip()]
    return cfg


def load_config() -> PluginConfig:
    path = config_path()
    if not path.exists():
        legacy = legacy_config_path()
        if legacy.exists():
            try:
                raw = json.loads(legacy.read_text(encoding="utf-8"))
                cfg = normalize(raw if isinstance(raw, dict) else {})
                save_config(cfg)
                return cfg
            except Exception:
                pass
        save_config(default_config())
        return default_config()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default_config()
    return normalize(raw if isinstance(raw, dict) else {})


def save_config(cfg: PluginConfig) -> None:
    config_path().write_text(json.dumps(asdict(cfg), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
