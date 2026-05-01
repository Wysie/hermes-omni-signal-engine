import json

import hermes_omni_signal_engine.plugin as plugin
from hermes_omni_signal_engine.runner import RunResult


SAMPLE_STATS = """
─────────────────────────────────────────────────
 OMNI Signal Report — Detail (today)
─────────────────────────────────────────────────
  Commands processed:  27
  Data Distilled:      45.6 KB → 12.5 KB
  Signal Ratio:        72.7% reduction
  Estimated Savings:   $0.025 USD
  Average Latency:     9.2ms
  RewindStore:         0 archived / 0 retrieved
  Collapse:            522 → 25 lines across 3 events
─────────────────────────────────────────────────
"""


def test_enhance_stats_estimates_tokens_and_subscription_value():
    enhanced = plugin._enhance_stats_output(SAMPLE_STATS)

    assert enhanced["commands_processed"] == 27
    assert enhanced["raw_kb"] == 45.6
    assert enhanced["distilled_kb"] == 12.5
    assert enhanced["saved_kb"] == 33.1
    assert enhanced["approx_tokens_saved_midpoint"] == 8275
    assert enhanced["approx_tokens_saved_range"] == {"low": 7356, "high": 9457}
    assert enhanced["codex_subscription_value"] == "context_hygiene_not_direct_bill_reduction"
    assert enhanced["rewind_retrieved"] == 0
    assert enhanced["raw_logs_needed_proxy"] == 0
    assert enhanced["over_summary_incidents"] is None


def test_tool_stats_includes_enhanced_stats(monkeypatch):
    monkeypatch.setattr(plugin, "_cfg", lambda: object())
    monkeypatch.setattr(
        plugin,
        "omni_stats",
        lambda period, cfg: RunResult(True, 0, SAMPLE_STATS, "", ["omni", "stats"]),
    )

    data = json.loads(plugin._tool_stats({"period": "today"}))

    assert data["ok"] is True
    assert data["enhanced"]["approx_tokens_saved_midpoint"] == 8275
    assert data["enhanced"]["raw_logs_needed_proxy"] == 0
