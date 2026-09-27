# Design note: explicit env-key removal for `mcp_servers.json`

Status: proposal (2026-09-27), fork-only. Related: `m2-demo-evidence.md` divergence 1
(RESOLVED via empty-string overrides), `parallax-telemetry-fixes.md` section 3.

## 1. Problem

`mcp_config.py::_connect_stdio_server` builds the child environment as:

```python
env = os.environ.copy()
if config.env:
    env.update(config.env)
```

A full parent-environment copy means every credential in the operator's shell
(`VOYAGE_API_KEY`, `BRAVE_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, cloud
tokens, ...) reaches **every** configured MCP server, regardless of whether that
server needs it. Two demonstrated consequences:

- **Least-privilege violation.** A benign helper gets keys it never asked for; a
  malicious or compromised MCP server exfiltrates the operator's whole shell
  credential set through its `env` access.
- **Semantic leaks.** parallax's optional memory/research integrations activate on
  key presence: the M2 demo's `surface` call made a real voyage-4 embedding call
  (`gen_ai.request.model=voyage-4`, `cost.usd=1.44e-6`) purely because
  `VOYAGE_API_KEY` happened to be exported in the shell.

Because `dict.update` can override but never **remove**, today's only defense is the
empty-string override trick: parallax normalizes blank keys to absent, so
`"VOYAGE_API_KEY": ""` neutralizes the leak. That works, but it is server-specific
(each server decides what "" means), undocumented as a contract, and reads like an
accident in the config file.

## 2. The reference point: the MCP SDK itself

The MCP Python SDK's `get_default_environment()` returns a **minimal allowlist** —
`PATH`, `PATHEXT`, Windows system roots, `TEMP`, `USERNAME`/`USERPROFILE` etc. —
precisely so a spawned stdio server does not inherit the parent's secrets by
default. PEAK deviates deliberately (full copy), presumably for usability: servers
just work without the operator enumerating what they need. The design question is
whether to keep the deviation and add an escape hatch, or converge on the SDK shape.

## 3. Options

### Option A — status quo plus a documented convention

Keep full-copy merge; document that servers should treat blank values as unset,
and that operators can neutralize leaks with `KEY: ""`. Zero code. Fails on the
merit that matters: it only works for servers that cooperate, and the operator
cannot tell from PEAK's side whether a given server honors it.

### Option B — explicit removal syntax (recommended)

Keep full-copy semantics by default, add a removal form interpreted by PEAK at
spawn time. Minimal, backward-compatible shape: a `null` value removes the key.

```json
"env": {
  "PARALLAX_BACKEND": "openai_compat",
  "VOYAGE_API_KEY": null,
  "BRAVE_API_KEY": null
}
```

Semantics: process `env` in two passes — apply all string values via `update`,
then drop every key whose configured value is `null`. `MCPServerConfig.env` widens
from `Dict[str, str]` to `Dict[str, Optional[str]]`; the config loader, the
`${VAR}` interpolation step, and `mcp-status` output all learn one rule. Optional
companion knob: a server- or global-level `inheritEnvironment: false` that starts
from the SDK allowlist instead of the full parent env (strict least privilege,
opt-in).

- Backward compatible: existing configs are all strings; `null` is new syntax.
- Cross-server: works against every MCP server, including ones that treat `""`
  as a real (empty) value.
- Auditable: the removal intent lives in the config file, reviewable in git
  (which is exactly why the secrets themselves must not live there).

### Option C — default to the SDK allowlist (converge)

Flip the default: `get_default_environment()` plus configured values. Strongest
security posture, but it is a silent behavior change for every existing user
config — servers that quietly rely on inherited variables (locale, proxy settings,
tool-specific paths) would start failing. If ever done, it is a major-version
change with a migration note, not a quiet PR.

## 4. Recommendation

**Option B** (null-removal), with `inheritEnvironment` noted as a possible
follow-up and Option C rejected for compatibility. Rationale: it turns a
server-specific accident into a documented, cross-server, config-reviewable
mechanism at the cost of a two-pass merge and a type widening; the empty-string
override stays valid for servers that normalize blanks, so the parallax demo
config needs no migration.

Scope for a first PEAK-side PR: the two-pass merge in `_connect_stdio_server`,
the `Dict[str, Optional[str]]` widening in `MCPServerConfig`, interpolation
pass-through for `null`, `mcp-status` display (show removed keys as `-KEY`), and
unit tests covering override-then-remove ordering, interpolation of non-null
values, and absent-key removal being a no-op.

## 5. Non-goals

- No secret storage in `mcp_servers.json` — `${VAR}` interpolation already
  keeps values in the environment; this note only changes which keys exist.
- No change to SSE/HTTP auth flows (they read `config.env` too; the same
  two-pass helper applies if those paths ever pass env to a subprocess).
- No upstream engagement: this is a fork-internal design note per the M3 memo.
