import os
import subprocess

from hermes_omni_signal_engine.config import PluginConfig
from hermes_omni_signal_engine.runner import distill_text, run_shell_command, sanitize_env


def test_sanitize_env_removes_dangerous_case_insensitive():
    cfg = PluginConfig(dangerous_env_vars=["LD_PRELOAD", "NODE_OPTIONS"])
    env = {"LD_PRELOAD": "x", "node_options": "y", "PATH": "/bin"}
    clean = sanitize_env(env, cfg)
    assert "LD_PRELOAD" not in clean
    assert "node_options" not in clean
    assert clean["PATH"] == "/bin"


def test_distill_text_falls_back_when_omni_missing():
    cfg = PluginConfig(omni_path="/definitely/missing/omni", preserve_raw_on_omni_failure=True)
    result = distill_text("raw output", "pytest", cfg)
    assert result.ok is False
    assert result.returncode == 127
    assert result.stdout == "raw output"


def test_run_shell_command_disabled_by_default():
    cfg = PluginConfig(enable_omni_cmd=False)
    result = run_shell_command("echo hi", cfg)
    assert result["ok"] is False
    assert "disabled" in result["error"]


def test_run_shell_command_distills_output(monkeypatch):
    calls = []

    def fake_find(cfg):
        return "/usr/bin/omni"

    def fake_run(argv, cfg, *, input_text=None, cwd=None, env_extra=None, timeout=None):
        from hermes_omni_signal_engine.runner import RunResult
        calls.append((argv, input_text, env_extra))
        if argv[0].endswith("sh"):
            return RunResult(True, 0, "hello\n", "", argv)
        return RunResult(True, 0, "distilled hello\n", "", argv)

    monkeypatch.setattr("hermes_omni_signal_engine.runner.find_omni", fake_find)
    monkeypatch.setattr("hermes_omni_signal_engine.runner.run_process", fake_run)
    cfg = PluginConfig(enable_omni_cmd=True)
    result = run_shell_command("echo hello", cfg)
    assert result["ok"] is True
    assert result["output"] == "distilled hello"
    assert calls[-1][2]["OMNI_CMD"] == "echo hello"
