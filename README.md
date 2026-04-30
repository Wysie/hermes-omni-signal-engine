# hermes-omni-signal-engine

Hermes Agent plugin for the [OMNI Semantic Signal Engine](https://github.com/fajarhide/omni): local-first terminal output distillation, rewind retrieval, stats, and diagnostics.

OMNI reduces noisy development output before it reaches an AI agent. This plugin bridges OMNI into Hermes without patching Hermes core.

## Features

- `omni_compress` — distill arbitrary text through OMNI without executing commands.
- `omni_rewind` — retrieve full raw output from OMNI RewindStore when a distilled summary was too aggressive.
- `omni_stats` — view OMNI token/cost savings.
- `omni_doctor` — run OMNI diagnostics.
- `omni_status` — inspect plugin config and resolved OMNI binary.
- `/omni` slash command — status, stats, doctor, config path.
- Optional `transform_terminal_output` hook — transparently distill Hermes terminal output before it enters model context.
- Optional `omni_cmd` command runner — execute a shell command and distill its output through OMNI. Disabled by default for safety.

## Safety model

This plugin is conservative by default:

- It does **not** execute shell commands unless `enable_omni_cmd` is explicitly set to `true`.
- It does **not** transparently rewrite Hermes terminal output unless `enable_transform_terminal_output` is explicitly set to `true`.
- It sanitizes dangerous environment variables before invoking OMNI or opt-in shell commands.
- It is local-first: terminal output is sent to the local `omni` binary, not to a cloud service by this plugin.
- If OMNI is missing or fails during compression, the plugin can preserve raw output instead of hiding it.

## Prerequisites

Install OMNI first:

```bash
brew install fajarhide/tap/omni
# or
curl -fsSL omni.weekndlabs.com/install | bash
```

Verify:

```bash
omni version
omni doctor
```

## Install in Hermes

Install this package into the same Python environment that runs Hermes — not system Python:

```bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_VENV="${HERMES_VENV:-$HERMES_HOME/hermes-agent/venv}"
HERMES_PY="${HERMES_PY:-$HERMES_VENV/bin/python}"
HERMES_BIN="${HERMES_BIN:-$HERMES_VENV/bin/hermes}"

"$HERMES_PY" -m pip install git+https://github.com/Wysie/hermes-omni-signal-engine.git
"$HERMES_BIN" plugins enable omni-signal-engine
"$HERMES_BIN" gateway restart
```

For local development:

```bash
git clone https://github.com/Wysie/hermes-omni-signal-engine.git
cd hermes-omni-signal-engine
$HOME/.hermes/hermes-agent/venv/bin/python -m pip install -e .
$HOME/.hermes/hermes-agent/venv/bin/hermes plugins enable omni-signal-engine
```

## Configuration

Config path:

```text
~/.hermes/plugin-data/omni-signal-engine/config.json
```

Safe default config:

```json
{
  "enabled": true,
  "omni_path": "omni",
  "timeout_seconds": 120,
  "sanitize_env": true,
  "enable_transform_terminal_output": false,
  "enable_omni_cmd": false,
  "max_input_chars": 1000000,
  "max_output_chars": 80000,
  "include_stderr_in_distillation": true,
  "preserve_raw_on_omni_failure": true
}
```

Enable transparent terminal output distillation only after testing:

```json
{
  "enable_transform_terminal_output": true
}
```

Enable `omni_cmd` only if you explicitly want an OMNI-backed command runner tool:

```json
{
  "enable_omni_cmd": true
}
```

Restart Hermes after config changes.

## Tools

### `omni_status`

Shows plugin config, config path, OMNI binary resolution, and OMNI version.

### `omni_compress`

Input:

```json
{
  "text": "long build log...",
  "command": "pytest -q"
}
```

Runs local OMNI pipe mode with `OMNI_CMD` set to the command context.

### `omni_rewind`

Input:

```json
{ "hash": "a3f8c2d1" }
```

Runs:

```bash
omni rewind a3f8c2d1
```

### `omni_stats`

Input:

```json
{ "period": "today" }
```

Allowed periods: `default`, `today`, `week`, `month`, `session`.

### `omni_doctor`

Input:

```json
{ "fix": false }
```

Runs `omni doctor`. `fix=true` runs `omni doctor --fix` and may modify local OMNI config.

### `omni_cmd` opt-in

Disabled by default. When enabled, it runs a shell command locally, then distills combined stdout/stderr through OMNI.

Input:

```json
{
  "command": "pytest -q",
  "cwd": "/path/to/project",
  "timeout_seconds": 300
}
```

Warning: this is terminal-equivalent. Do not enable it in environments where the model should not execute shell commands.

## Slash command

Inside Hermes:

```text
/omni status
/omni stats today
/omni doctor
/omni doctor --fix
/omni config-path
/omni reset-config
```

## Development

```bash
python -m pip install -e . pytest
python -m pytest
```

## Design notes

The OpenClaw OMNI plugin exposes `omni_cmd`. Hermes has a richer plugin surface, so this package supports both explicit tools and a native terminal-output transform hook. The transform hook is off by default because lossless access to raw terminal output matters during coding.

## License

MIT
