from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import PluginConfig


@dataclass
class RunResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    command: list[str]
    timed_out: bool = False
    error: str = ""

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "command": self.command,
            "timed_out": self.timed_out,
            "error": self.error,
        }


def json_dumps(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def find_omni(cfg: PluginConfig) -> str | None:
    candidate = cfg.omni_path.strip() or "omni"
    if os.path.sep in candidate or (os.path.altsep and os.path.altsep in candidate):
        return candidate if Path(candidate).exists() else None
    return shutil.which(candidate)


def sanitize_env(env: dict[str, str] | None, cfg: PluginConfig) -> dict[str, str]:
    base = dict(os.environ if env is None else env)
    if not cfg.sanitize_env:
        return base
    deny = {name.upper() for name in cfg.dangerous_env_vars}
    return {k: v for k, v in base.items() if k.upper() not in deny}


def run_process(
    argv: list[str],
    cfg: PluginConfig,
    *,
    input_text: str | None = None,
    cwd: str | None = None,
    env_extra: dict[str, str] | None = None,
    timeout: int | None = None,
) -> RunResult:
    env = sanitize_env(None, cfg)
    if env_extra:
        env.update({str(k): str(v) for k, v in env_extra.items()})
    try:
        cp = subprocess.run(
            argv,
            input=input_text,
            text=True,
            capture_output=True,
            cwd=cwd or None,
            env=env,
            timeout=timeout or cfg.timeout_seconds,
            shell=False,
        )
        return RunResult(cp.returncode == 0, cp.returncode, cp.stdout or "", cp.stderr or "", argv)
    except subprocess.TimeoutExpired as exc:
        return RunResult(
            False,
            124,
            exc.stdout if isinstance(exc.stdout, str) else "",
            exc.stderr if isinstance(exc.stderr, str) else "",
            argv,
            timed_out=True,
            error=f"Timed out after {timeout or cfg.timeout_seconds}s",
        )
    except Exception as exc:
        return RunResult(False, -1, "", "", argv, error=str(exc))


def omni_version(cfg: PluginConfig) -> RunResult:
    omni = find_omni(cfg) or cfg.omni_path
    return run_process([omni, "version"], cfg, timeout=min(cfg.timeout_seconds, 30))


def distill_text(text: str, command: str, cfg: PluginConfig, *, cwd: str | None = None) -> RunResult:
    omni = find_omni(cfg)
    if not omni:
        return RunResult(False, 127, text if cfg.preserve_raw_on_omni_failure else "", "omni binary not found", [cfg.omni_path], error="omni binary not found")
    if len(text) > cfg.max_input_chars:
        text = text[: cfg.max_input_chars] + f"\n[hermes-omni: input truncated to {cfg.max_input_chars} chars before OMNI]\n"
    env_extra = {"OMNI_CMD": command or "hermes"}
    # No arguments + stdin triggers OMNI pipe mode. OMNI_CMD supplies command context.
    result = run_process([omni], cfg, input_text=text, cwd=cwd, env_extra=env_extra)
    if not result.ok and cfg.preserve_raw_on_omni_failure:
        result.stdout = text
    if len(result.stdout) > cfg.max_output_chars:
        result.stdout = result.stdout[: cfg.max_output_chars] + f"\n[hermes-omni: output truncated to {cfg.max_output_chars} chars]\n"
    return result


def run_shell_command(command: str, cfg: PluginConfig, *, cwd: str | None = None, timeout: int | None = None) -> dict:
    if not cfg.enable_omni_cmd:
        return {"ok": False, "error": "omni_cmd is disabled by config; set enable_omni_cmd=true and restart Hermes to expose command execution."}
    if not command or not command.strip():
        return {"ok": False, "error": "command is required"}
    if platform.system().lower().startswith("win"):
        argv = ["cmd", "/C", command]
    else:
        argv = ["/bin/sh", "-c", command]
    raw = run_process(argv, cfg, cwd=cwd, timeout=timeout or cfg.timeout_seconds)
    combined = raw.stdout
    if cfg.include_stderr_in_distillation and raw.stderr.strip():
        combined = combined + ("\n" if combined else "") + "[stderr]\n" + raw.stderr
    distilled = distill_text(combined, command, cfg, cwd=cwd)
    return {
        "ok": raw.ok,
        "exit_code": raw.returncode,
        "output": distilled.stdout.strip(),
        "omni_ok": distilled.ok,
        "omni_error": distilled.error or distilled.stderr.strip(),
        "raw_stdout_bytes": len(raw.stdout.encode()),
        "raw_stderr_bytes": len(raw.stderr.encode()),
        "distilled_bytes": len(distilled.stdout.encode()),
        "cwd": cwd or os.getcwd(),
    }


def omni_rewind(hash_value: str, cfg: PluginConfig) -> RunResult:
    omni = find_omni(cfg) or cfg.omni_path
    return run_process([omni, "rewind", hash_value], cfg)


def omni_stats(period: str, cfg: PluginConfig) -> RunResult:
    allowed = {"today": "--today", "week": "--week", "month": "--month", "session": "--session", "default": ""}
    flag = allowed.get(period or "default", "")
    argv = [find_omni(cfg) or cfg.omni_path, "stats"]
    if flag:
        argv.append(flag)
    return run_process(argv, cfg)


def omni_doctor(fix: bool, cfg: PluginConfig) -> RunResult:
    argv = [find_omni(cfg) or cfg.omni_path, "doctor"]
    if fix:
        argv.append("--fix")
    return run_process(argv, cfg, timeout=max(cfg.timeout_seconds, 180 if fix else 60))
