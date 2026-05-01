# Security Policy

`hermes-omni-plugin` is a local bridge to the OMNI CLI. It does not intentionally send terminal output to external services.

## Important risks

- `omni_cmd` is terminal-equivalent and can execute arbitrary shell commands. It is disabled by default.
- Transparent terminal output distillation can hide details from the model. It is disabled by default.
- OMNI stores local state under `~/.omni`, including RewindStore and stats.

## Environment sanitization

Before invoking OMNI or opt-in shell commands, the plugin removes dangerous environment variables such as `LD_PRELOAD`, `DYLD_INSERT_LIBRARIES`, `NODE_OPTIONS`, `PYTHONPATH`, `BASH_ENV`, and `GIT_ASKPASS`.

## Reporting issues

Open a GitHub issue with reproduction steps, platform, Hermes version, OMNI version, and plugin config. Do not paste secrets.
