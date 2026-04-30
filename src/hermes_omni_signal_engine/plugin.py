from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .config import config_path, load_config, save_config, default_config
from .runner import (
    distill_text,
    find_omni,
    json_dumps,
    omni_doctor,
    omni_rewind,
    omni_stats,
    omni_version,
    run_shell_command,
)

_TOOLSET = "omni"
_REGISTERED = False


def _cfg():
    return load_config()


def _omni_available() -> bool:
    return find_omni(_cfg()) is not None


def _status_dict() -> dict:
    cfg = _cfg()
    version = omni_version(cfg) if find_omni(cfg) else None
    return {
        "plugin": "omni-signal-engine",
        "config_path": str(config_path()),
        "omni_path_configured": cfg.omni_path,
        "omni_path_resolved": find_omni(cfg),
        "omni_available": find_omni(cfg) is not None,
        "omni_version": (version.stdout.strip() if version and version.ok else None),
        "config": asdict(cfg),
    }


def _tool_status(args: dict | None = None, **_kw) -> str:
    return json_dumps(_status_dict())


def _tool_compress(args: dict | None = None, **_kw) -> str:
    cfg = _cfg()
    args = args or {}
    text = args.get("text")
    if not isinstance(text, str) or not text:
        return json_dumps({"ok": False, "error": "text is required"})
    command = str(args.get("command") or "hermes")
    cwd = args.get("cwd") if isinstance(args.get("cwd"), str) else None
    result = distill_text(text, command, cfg, cwd=cwd)
    return json_dumps({
        "ok": result.ok,
        "output": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "error": result.error,
        "returncode": result.returncode,
        "input_bytes": len(text.encode()),
        "output_bytes": len(result.stdout.encode()),
    })


def _tool_cmd(args: dict | None = None, **_kw) -> str:
    cfg = _cfg()
    args = args or {}
    timeout = args.get("timeout_seconds")
    try:
        timeout_i = int(timeout) if timeout is not None else None
    except Exception:
        timeout_i = None
    result = run_shell_command(
        str(args.get("command") or ""),
        cfg,
        cwd=args.get("cwd") if isinstance(args.get("cwd"), str) else None,
        timeout=timeout_i,
    )
    return json_dumps(result)


def _tool_rewind(args: dict | None = None, **_kw) -> str:
    cfg = _cfg()
    args = args or {}
    hash_value = str(args.get("hash") or args.get("hash_value") or "").strip()
    if not hash_value:
        return json_dumps({"ok": False, "error": "hash is required"})
    result = omni_rewind(hash_value, cfg)
    return json_dumps(result.as_dict() | {"output": result.stdout.strip()})


def _tool_stats(args: dict | None = None, **_kw) -> str:
    cfg = _cfg()
    args = args or {}
    period = str(args.get("period") or "default")
    result = omni_stats(period, cfg)
    return json_dumps(result.as_dict() | {"output": result.stdout.strip()})


def _tool_doctor(args: dict | None = None, **_kw) -> str:
    cfg = _cfg()
    args = args or {}
    fix = bool(args.get("fix", False))
    result = omni_doctor(fix, cfg)
    return json_dumps(result.as_dict() | {"output": result.stdout.strip()})


def _slash(raw_args: str) -> str:
    sub = (raw_args or "").strip().split(maxsplit=1)
    cmd = sub[0].lower() if sub else "status"
    if cmd in {"status", "show"}:
        return json_dumps(_status_dict())
    if cmd == "stats":
        period = sub[1] if len(sub) > 1 else "default"
        return _tool_stats({"period": period})
    if cmd == "doctor":
        fix = len(sub) > 1 and sub[1].strip() in {"--fix", "fix", "true"}
        return _tool_doctor({"fix": fix})
    if cmd == "config-path":
        return str(config_path())
    if cmd == "reset-config":
        save_config(default_config())
        return f"Reset OMNI plugin config at {config_path()}"
    return "Usage: /omni [status|stats [today|week|month|session]|doctor [--fix]|config-path|reset-config]"


def _transform_terminal_output(*, command: str, output: str, returncode: int = 0, task_id: str = "", env_type: str = "", **_kw):
    cfg = _cfg()
    if not cfg.enabled or not cfg.enable_transform_terminal_output:
        return None
    if not output:
        return None
    result = distill_text(output, command or "terminal", cfg)
    if not result.stdout or result.stdout == output:
        return None
    header = "[OMNI distilled terminal output"
    if result.returncode != 0:
        header += f"; omni_exit={result.returncode}"
    header += "]\n"
    return header + result.stdout.strip()


def register(ctx) -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    ctx.register_tool(
        name="omni_status",
        toolset=_TOOLSET,
        schema={"name": "omni_status", "description": "Show OMNI Signal Engine plugin status, resolved binary path, and current config.", "parameters": {"type": "object", "properties": {}}},
        handler=_tool_status,
        check_fn=lambda: True,
        requires_env=[],
        description="OMNI plugin status",
        emoji="🛰️",
    )
    ctx.register_tool(
        name="omni_compress",
        toolset=_TOOLSET,
        schema={"name": "omni_compress", "description": "Distill arbitrary text through the local OMNI pipeline without executing commands.", "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "command": {"type": "string", "default": "hermes"}, "cwd": {"type": "string"}}, "required": ["text"]}},
        handler=_tool_compress,
        check_fn=_omni_available,
        requires_env=[],
        description="Distill text with OMNI",
        emoji="💎",
    )
    ctx.register_tool(
        name="omni_rewind",
        toolset=_TOOLSET,
        schema={"name": "omni_rewind", "description": "Retrieve full raw output stored by OMNI RewindStore.", "parameters": {"type": "object", "properties": {"hash": {"type": "string"}}, "required": ["hash"]}},
        handler=_tool_rewind,
        check_fn=_omni_available,
        requires_env=[],
        description="Retrieve OMNI rewind output",
        emoji="⏪",
    )
    ctx.register_tool(
        name="omni_stats",
        toolset=_TOOLSET,
        schema={"name": "omni_stats", "description": "Show OMNI token/cost savings statistics.", "parameters": {"type": "object", "properties": {"period": {"type": "string", "enum": ["default", "today", "week", "month", "session"], "default": "default"}}}},
        handler=_tool_stats,
        check_fn=_omni_available,
        requires_env=[],
        description="Show OMNI stats",
        emoji="📊",
    )
    ctx.register_tool(
        name="omni_doctor",
        toolset=_TOOLSET,
        schema={"name": "omni_doctor", "description": "Run OMNI diagnostics. Set fix=true only when you explicitly want OMNI to repair local config.", "parameters": {"type": "object", "properties": {"fix": {"type": "boolean", "default": False}}}},
        handler=_tool_doctor,
        check_fn=_omni_available,
        requires_env=[],
        description="Run OMNI doctor",
        emoji="🩺",
    )
    ctx.register_tool(
        name="omni_cmd",
        toolset=_TOOLSET,
        schema={"name": "omni_cmd", "description": "Opt-in terminal-equivalent command runner: execute a shell command and distill its output through OMNI. Disabled by default in plugin config.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "cwd": {"type": "string"}, "timeout_seconds": {"type": "integer"}}, "required": ["command"]}},
        handler=_tool_cmd,
        check_fn=lambda: _omni_available() and _cfg().enable_omni_cmd,
        requires_env=[],
        description="Run command through OMNI (opt-in)",
        emoji="⚙️",
    )
    ctx.register_hook("transform_terminal_output", _transform_terminal_output)
    ctx.register_command("omni", handler=_slash, description="OMNI Signal Engine status, stats, and diagnostics", args_hint="status|stats|doctor")
    _REGISTERED = True
