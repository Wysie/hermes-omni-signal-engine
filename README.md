# hermes-omni-plugin

Hermes Agent plugin for the [OMNI Semantic Signal Engine](https://github.com/fajarhide/omni): local-first terminal output distillation, rewind retrieval, stats, and diagnostics.

OMNI reduces noisy development output before it reaches an AI agent. This plugin bridges OMNI into Hermes without patching Hermes core.

## Features

- `omni_compress` — distill arbitrary text through OMNI without executing commands.
- `omni_rewind` — retrieve full raw output from OMNI RewindStore when a distilled summary was too aggressive.
- `omni_stats` — view OMNI token/cost savings.
- `omni_doctor` — run OMNI diagnostics.
- `omni_status` — inspect plugin config and resolved OMNI binary.
- `/omni` slash command — status, stats, doctor, config path.
- `transform_terminal_output` hook — transparently distill Hermes terminal output before it enters model context. Enabled by default.
- Optional `omni_cmd` command runner — execute a shell command and distill its output through OMNI. Disabled by default for safety.

## Safety model

This plugin balances visible value with conservative command execution defaults:

- It transparently distills Hermes terminal output by default, so users see the plugin working immediately after install and restart.
- It marks transformed output with `[OMNI distilled terminal output]`, so agents and users know the output is distilled rather than raw.
- It does **not** execute shell commands unless `enable_omni_cmd` is explicitly set to `true`.
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

"$HERMES_PY" -m pip install git+https://github.com/Wysie/hermes-omni-plugin.git
```

Enable the pip entry-point plugin by adding `hermes-omni-plugin` to `plugins.enabled` in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - hermes-omni-plugin
```

If you already have other enabled plugins, keep them and add `hermes-omni-plugin` as another list item:

```yaml
plugins:
  enabled:
    - disk-cleanup
    - drawthings-grpc
    - hermes-omni-plugin
```

Restart Hermes so the new entry point is discovered:

```bash
"$HERMES_BIN" gateway restart
# or start a fresh `hermes chat` / TUI session
```

Note: on some Hermes versions, `hermes plugins enable hermes-omni-plugin` only checks directory/bundled plugins and may say the plugin is not installed even though the pip entry point is installed correctly. Manual `plugins.enabled` config is the reliable path for pip-installed plugins.

Early versions used the plugin key `omni-signal-engine`; the package keeps that entry-point alias for backward compatibility, but new installs should use `hermes-omni-plugin`.

For local development:

```bash
git clone https://github.com/Wysie/hermes-omni-plugin.git
cd hermes-omni-plugin
$HOME/.hermes/hermes-agent/venv/bin/python -m pip install -e .
```

Then add `hermes-omni-plugin` to `plugins.enabled` as shown above and restart Hermes.

## Update

If you installed from GitHub, update the plugin in the Hermes Python environment and restart Hermes:

```bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_VENV="${HERMES_VENV:-$HERMES_HOME/hermes-agent/venv}"
HERMES_PY="${HERMES_PY:-$HERMES_VENV/bin/python}"
HERMES_BIN="${HERMES_BIN:-$HERMES_VENV/bin/hermes}"

"$HERMES_PY" -m pip install --upgrade --force-reinstall git+https://github.com/Wysie/hermes-omni-plugin.git
"$HERMES_BIN" gateway restart
```

If you installed an editable local development checkout:

```bash
cd /path/to/hermes-omni-plugin
git pull
$HOME/.hermes/hermes-agent/venv/bin/python -m pip install -e .
$HOME/.hermes/hermes-agent/venv/bin/hermes gateway restart
```

If/when the package is published to PyPI, users can update with:

```bash
$HOME/.hermes/hermes-agent/venv/bin/python -m pip install --upgrade hermes-omni-plugin
$HOME/.hermes/hermes-agent/venv/bin/hermes gateway restart
```

The config file at `~/.hermes/plugin-data/hermes-omni-plugin/config.json` is preserved across package updates. Users only need to re-check `plugins.enabled` if they are migrating from the old `omni-signal-engine` key or reinstalling Hermes from scratch.

Verify discovery after restart:

```bash
$HOME/.hermes/hermes-agent/venv/bin/python - <<'PY'
from hermes_cli.plugins import PluginManager
pm = PluginManager()
pm.discover_and_load()
for key, plugin in pm._plugins.items():
    if key == "hermes-omni-plugin":
        print(key, "source=", plugin.manifest.source, "enabled=", plugin.enabled, "error=", plugin.error)
PY
```

Expected output includes `source= entrypoint`, `enabled= True`, and `error= None`.

## Configuration

Config path:

```text
~/.hermes/plugin-data/hermes-omni-plugin/config.json
```

Default config:

```json
{
  "enabled": true,
  "omni_path": "omni",
  "timeout_seconds": 120,
  "sanitize_env": true,
  "dangerous_env_vars": [
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
    "SSH_ASKPASS"
  ],
  "enable_transform_terminal_output": true,
  "enable_omni_cmd": false,
  "max_input_chars": 1000000,
  "max_output_chars": 80000,
  "include_stderr_in_distillation": true,
  "preserve_raw_on_omni_failure": true
}
```

### Config option reference

| Option | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | boolean | `true` | Master switch for OMNI integration. When `false`, the terminal transform hook passes raw output through unchanged and explicit OMNI tools should be treated as disabled by policy. |
| `omni_path` / `omniPath` | string | `"omni"` | Path or command name for the OMNI CLI binary. Use an absolute path if Hermes' runtime `PATH` cannot find `omni`. `omniPath` is accepted as a camelCase alias for compatibility. |
| `timeout_seconds` | integer | `120` | Maximum seconds to wait for OMNI CLI operations such as compress, rewind, stats, doctor, or opt-in command execution. Values are clamped between `1` and `3600`. |
| `sanitize_env` | boolean | `true` | Remove risky environment variables before invoking OMNI or opt-in shell commands. Keep this enabled unless you are debugging a specific environment issue. |
| `dangerous_env_vars` | string array | see config above | Environment variable names removed when `sanitize_env` is enabled. Defaults cover shell startup hooks, language runtime injection hooks, dynamic linker injection, and credential prompt helpers. |
| `enable_transform_terminal_output` | boolean | `true` | Enables the native Hermes `transform_terminal_output` hook so terminal output is automatically distilled before entering model context. On by default so the plugin visibly reduces terminal noise after install. Disable when you need exact raw terminal logs for subtle debugging. |
| `enable_omni_cmd` | boolean | `false` | Registers/enables the terminal-equivalent `omni_cmd` tool. Off by default because it executes shell commands and can have side effects. |
| `max_input_chars` | integer | `1000000` | Maximum characters accepted for OMNI distillation input. Longer text is truncated before OMNI is called. Values are clamped between `1000` and `20000000`. |
| `max_output_chars` | integer | `80000` | Maximum characters returned from distilled or raw fallback output to Hermes. Values are clamped between `1000` and `2000000`. |
| `include_stderr_in_distillation` | boolean | `true` | For `omni_cmd`, include stderr together with stdout before distillation. Useful for build/test failures where the important signal is often on stderr. |
| `preserve_raw_on_omni_failure` | boolean | `true` | If OMNI is missing, times out, or errors, return clipped raw output instead of hiding the command result. Set `false` only if you prefer failures to surface as errors rather than raw fallback text. |

Boolean options accept JSON booleans and common string forms such as `"true"`, `"false"`, `"yes"`, `"no"`, `"on"`, and `"off"`.

Restart Hermes after config changes so long-running gateway or TUI processes pick up the new values.

Disable transparent terminal output distillation when you need exact raw terminal logs, or when another enabled Hermes plugin already transforms terminal output:

```json
{
  "enable_transform_terminal_output": false
}
```

### Compatibility with other terminal output transformers

Hermes runs every registered `transform_terminal_output` hook in sequence. If more than one plugin transforms the same terminal output, later hooks receive already-transformed text rather than the original raw stdout/stderr.

Do not enable OMNI's transparent terminal-output transform together with another plugin that also modifies terminal output, such as `hermes-rtk-optimizer`. Choose one transformer for automatic terminal output handling:

```json
{
  "enable_transform_terminal_output": false
}
```

You can still keep `hermes-omni-plugin` enabled for explicit tools such as `omni_compress`, `omni_rewind`, `omni_stats`, `omni_doctor`, and `omni_status` while another plugin owns terminal-output transformation.

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

The plugin validates rewind hashes before invoking OMNI: hashes must be 8–128 hexadecimal characters. Invalid hashes are rejected before subprocess execution.

### `omni_stats`

Input:

```json
{ "period": "today" }
```

Allowed periods: `default`, `today`, `week`, `month`, `session`.

The tool calls `omni stats --json` as the deterministic source of truth for enhanced fields, falling back to human-readable parsing only for older OMNI versions where JSON stats are unavailable. It returns OMNI's original human-readable report plus an `enhanced` object with Hermes-friendly derived metrics:

- `commands_processed`
- `input_tokens`, `output_tokens`, and `tokens_saved` from OMNI JSON stats
- `approx_tokens_saved_range` and `approx_tokens_saved_midpoint` (exactly `tokens_saved` when JSON stats are available; 3.5–4.5 chars/token fallback for older text stats)
- `api_equivalent_savings_usd` from OMNI's own estimate
- `average_latency_ms`
- `rewind_archived`, `rewind_retrieved`, and `raw_logs_needed_proxy`
- `codex_subscription_value`, which marks subscription-backed usage as context hygiene rather than direct bill reduction
- `over_summary_incidents`, currently `null` because quality mistakes are not automatically detectable

These enhanced fields are estimates/proxies. Exact token counts and Codex subscription quota impact depend on the model/provider runtime.

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

The reset command creates a timestamped `config.json.<UTC>.bak` backup beside the config file before overwriting it.

## Development

```bash
python -m pip install -e . pytest
python -m pytest
```

## Design notes

The OpenClaw OMNI plugin exposes `omni_cmd`. Hermes has a richer plugin surface, so this package supports both explicit tools and a native terminal-output transform hook. The transform hook is on by default so a newly installed plugin has visible effect; `omni_cmd` stays off by default because it is terminal-equivalent and can have side effects.

## License

MIT
