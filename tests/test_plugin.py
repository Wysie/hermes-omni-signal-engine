import json

import hermes_omni_signal_engine.plugin as plugin
from hermes_omni_signal_engine.config import PluginConfig
from hermes_omni_signal_engine.runner import RunResult


class Ctx:
    def __init__(self):
        self.tools = []
        self.hooks = []
        self.commands = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_hook(self, name, cb):
        self.hooks.append((name, cb))

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands.append((name, handler, description, args_hint))


def test_register_adds_tools_hook_and_slash_command(monkeypatch):
    plugin._REGISTERED = False
    ctx = Ctx()
    plugin.register(ctx)
    names = {t["name"] for t in ctx.tools}
    assert {"omni_status", "omni_compress", "omni_rewind", "omni_stats", "omni_doctor", "omni_cmd"} <= names
    assert any(name == "transform_terminal_output" for name, _ in ctx.hooks)
    assert any(c[0] == "omni" for c in ctx.commands)


def test_transform_terminal_output_disabled_by_default(monkeypatch):
    monkeypatch.setattr(plugin, "load_config", lambda: PluginConfig(enable_transform_terminal_output=False))
    out = plugin._transform_terminal_output(command="pytest", output="raw", returncode=0)
    assert out is None


def test_transform_terminal_output_distills_when_enabled(monkeypatch):
    cfg = PluginConfig(enable_transform_terminal_output=True)
    monkeypatch.setattr(plugin, "load_config", lambda: cfg)
    monkeypatch.setattr(plugin, "distill_text", lambda output, command, cfg: RunResult(True, 0, "distilled", "", ["omni"]))
    out = plugin._transform_terminal_output(command="pytest", output="raw", returncode=0)
    assert out == "[OMNI distilled terminal output]\ndistilled"


def test_transform_terminal_output_returns_none_and_logs_on_distill_failure(monkeypatch, caplog):
    cfg = PluginConfig(enable_transform_terminal_output=True)
    monkeypatch.setattr(plugin, "load_config", lambda: cfg)
    # OMNI fails: returncode=1, error="omni internal error", stdout unchanged
    monkeypatch.setattr(
        plugin, "distill_text",
        lambda output, command, cfg: RunResult(False, 1, output, "omni internal error", ["omni"], error="omni internal error"),
    )
    with caplog.at_level("DEBUG", logger="hermes_omni_signal_engine.plugin"):
        out = plugin._transform_terminal_output(command="pytest", output="raw", returncode=0)
    assert out is None
    assert "OMNI distillation failed" in caplog.text
    assert "omni_exit=1" in caplog.text


def test_tool_compress_requires_text(monkeypatch):
    result = json.loads(plugin._tool_compress({}))
    assert result["ok"] is False
    assert "text" in result["error"]


def test_slash_status_returns_json(monkeypatch):
    monkeypatch.setattr(plugin, "_status_dict", lambda: {"plugin": "hermes-omni-plugin"})
    data = json.loads(plugin._slash("status"))
    assert data["plugin"] == "hermes-omni-plugin"
