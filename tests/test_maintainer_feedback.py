import json

import hermes_omni_signal_engine.plugin as plugin
from hermes_omni_signal_engine.config import PluginConfig, backup_config, config_path, load_config, save_config
from hermes_omni_signal_engine.runner import RunResult, omni_stats


def test_rewind_rejects_non_hex_hash(monkeypatch):
    called = False

    def fake_rewind(hash_value, cfg):
        nonlocal called
        called = True
        return RunResult(True, 0, "raw", "", ["omni", "rewind", hash_value])

    monkeypatch.setattr(plugin, "omni_rewind", fake_rewind)
    data = json.loads(plugin._tool_rewind({"hash": "abc123; rm -rf /"}))

    assert data["ok"] is False
    assert "invalid hash" in data["error"]
    assert called is False


def test_rewind_accepts_hex_hash(monkeypatch):
    seen = []

    def fake_rewind(hash_value, cfg):
        seen.append(hash_value)
        return RunResult(True, 0, "raw", "", ["omni", "rewind", hash_value])

    monkeypatch.setattr(plugin, "omni_rewind", fake_rewind)
    data = json.loads(plugin._tool_rewind({"hash": "a3f8c2d1"}))

    assert data["ok"] is True
    assert seen == ["a3f8c2d1"]


def test_parse_kb_uses_binary_units():
    assert plugin._parse_kb("1024", "B") == 1
    assert plugin._parse_kb("1", "MB") == 1024
    assert plugin._parse_kb("1", "GB") == 1024 * 1024


def test_omni_stats_json_flag(monkeypatch):
    calls = []

    def fake_find(cfg):
        return "/usr/bin/omni"

    def fake_run(argv, cfg):
        calls.append(argv)
        return RunResult(True, 0, "{}", "", argv)

    monkeypatch.setattr("hermes_omni_signal_engine.runner.find_omni", fake_find)
    monkeypatch.setattr("hermes_omni_signal_engine.runner.run_process", fake_run)

    omni_stats("today", PluginConfig(), json_output=True)

    assert calls == [["/usr/bin/omni", "stats", "--json", "--today"]]


def test_tool_stats_prefers_json_source(monkeypatch):
    human = "OMNI Signal Report\n  RewindStore:         0 archived │ 0 retrieved\n"
    stats_json = json.dumps(
        {
            "periods": [
                {
                    "label": "today",
                    "commands": 3,
                    "input_tokens": 1000,
                    "output_tokens": 250,
                    "savings_pct": 75.0,
                    "usd_saved": 0.01,
                },
                {
                    "label": "all_time",
                    "commands": 4,
                    "input_tokens": 1200,
                    "output_tokens": 600,
                    "savings_pct": 50.0,
                    "usd_saved": 0.02,
                },
            ],
            "commands": [{"command": "pytest", "count": 3, "savings_pct": 75.0}],
            "agents": [{"agent": "aider", "count": 3, "savings_pct": 75.0}],
            "rewind": {"archived": 1, "retrieved": 2},
            "avg_latency_ms": 8.5,
        }
    )

    def fake_stats(period, cfg, *, json_output=False):
        if json_output:
            return RunResult(True, 0, stats_json, "", ["omni", "stats", "--json"])
        return RunResult(True, 0, human, "", ["omni", "stats"])

    monkeypatch.setattr(plugin, "_cfg", lambda: PluginConfig())
    monkeypatch.setattr(plugin, "omni_stats", fake_stats)

    data = json.loads(plugin._tool_stats({"period": "today"}))

    assert data["enhanced"]["stats_source"] == "omni_stats_json"
    assert data["enhanced"]["commands_processed"] == 3
    assert data["enhanced"]["tokens_saved"] == 750
    assert data["enhanced"]["rewind_retrieved"] == 2
    assert data["enhanced"]["average_latency_ms"] == 8.5


def test_backup_config_creates_timestamped_copy(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    cfg = PluginConfig(omni_path="/custom/omni")
    save_config(cfg)

    backup = backup_config()
    save_config(PluginConfig())

    assert backup is not None
    assert backup.exists()
    assert backup.name.startswith("config.json.")
    assert backup.name.endswith(".bak")
    assert json.loads(backup.read_text())["omni_path"] == "/custom/omni"
    assert load_config().omni_path == "omni"


def test_slash_reset_config_reports_backup(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    save_config(PluginConfig(omni_path="/custom/omni"))

    msg = plugin._slash("reset-config")

    assert "backup:" in msg
    assert load_config().omni_path == "omni"
    backups = list(config_path().parent.glob("config.json.*.bak"))
    assert len(backups) == 1
