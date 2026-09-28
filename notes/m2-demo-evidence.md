# M2 demo evidence — zero-PEAK-code parallax demo

Run date: 2026-09-27. PEAK fork `main` at `1592da0`; parallax fork `main` at `e7f12f8`
(PRs #107 + #108 merged — keyless OpenAI-compatible endpoints). Backend: Ollama 0.34.0
at `http://localhost:11434`, model `qwen2.5:7b`. Result: **exit 0** — the full
`data_discovery` phase ran end-to-end with parallax tools available in the workbench.
Full transcript committed verbatim as `notes/m2-demo-transcript.log`; quotes below are verbatim.

## 1. Configuration (the only wiring added)

Both files are gitignored and stay uncommitted; snippets reproduced verbatim. No secrets:
the parallax side is keyless by contract (PR #108); `sk-local` is a placeholder the
OpenAI-compatible client accepts and Ollama ignores.

### `mcp_servers.json`

```json
{
  "mcpServers": {
    "parallax": {
      "transport": "stdio",
      "command": "D:/Projects/mcp-parallax-m1/target/debug/mcp-parallax.exe",
      "args": [],
      "env": {
        "PARALLAX_BACKEND": "openai_compat",
        "OPENAI_API_BASE": "http://localhost:11434/v1",
        "OPENAI_MODEL": "qwen2.5:7b",
        "DATABASE_PATH": "C:/Users/rbsmi/AppData/Local/Temp/parallax-peak-m2.db"
      },
      "description": "parallax corrective tools on a keyless local Ollama backend (M2 demo)"
    }
  },
  "serverGroups": {
    "data_discovery": [
      "parallax"
    ]
  }
}
```

`data_discovery` is a PEAK group whose agent mapping is code (`identify_data_sources()`
runs Data_Discovery_Agent + Discovery_Critic_Agent as a RoundRobinGroupChat terminated by
`TextMentionTermination("YYY-TERMINATE-YYY")`); adding parallax to the group is the
config-only part. Validated pre-run with `uv run mcp-status -v` -> "Ready / All MCP
servers are properly configured!".

### `model_config.json` — `ollama-local` provider (shipped example) + model entry

```json
{
  "version": "1",
  "providers": {
    "ollama-local": {
      "type": "openai",
      "config": {
        "api_key": "sk-local",
        "base_url": "http://localhost:11434/v1"
      },
      "models": {
        "qwen2.5:7b": {
          "model_info": {
            "id": "qwen2.5:7b",
            "object": "model",
            "owned_by": "local",
            "family": "qwen2",
            "vision": false,
            "audio": false,
            "function_calling": true,
            "json_output": true,
            "structured_output": true,
            "input": {
              "max_tokens": 32768
            },
            "output": {
              "max_tokens": 8192
            },
            "tokenizer": "tiktoken-gpt-4o"
          }
        }
      }
    }
  },
  "defaults": {
    "provider": "ollama-local",
    "model": "qwen2.5:7b"
  },
  "groups": {},
  "agents": {}
}
```

`function_calling: true` matters: qwen2.5:7b emitted a real tool call, and those flags
gate whether the tool schema is offered at all.

## 2. Transcript excerpts (verbatim)

PEAK's MCP client (name `mcp`, v0.1.0) initialized the stdio server and negotiated
protocol 2025-11-25. parallax resolved all 12 call sites (11 `judgment`, 1 `bulk`)
to `qwen2.5:7b`, then booted on the local backend (routing log abridged):

```
2026-09-27T15:37:13.123149Z  INFO mcp_parallax::server: routing resolved call_site="verify" tier="judgment" model=qwen2.5:7b source=ANTHROPIC_MODEL
... (12 routing-resolved lines: 11 tier="judgment", 1 tier="bulk")
2026-09-27T15:37:13.123319Z  INFO mcp_parallax::server: routing table complete call_sites=12 distinct_models=1 effort_overridable_per_call=true
2026-09-27T15:37:13.126205Z  INFO mcp_parallax: parallax: serving MCP over stdio database=C:/Users/rbsmi/AppData/Local/Temp/parallax-peak-m2.db backend="openai_compat" model=qwen2.5:7b ensemble_k=3 timeout_ms=120000 max_retries=3 telemetry=false
```

The one tool call the agent made:

```
---------- ToolCallRequestEvent (Data_Discovery_Agent) ----------
[FunctionCall(id='call_93o89w7b', arguments='{"session_id":"M2_demo_run","prompt":"I am planning to integrate the MCP tools into the M2 workbench. Can you recall any relevant memories from previous sessions?"}', name='surface')]
2026-09-27T15:37:20.576875Z  INFO serve_inner: mcp_parallax::telemetry: invocation recorded invocation.id=aeeeff07-526d-4d41-9a68-4bd04370592f session.id=c20e2a3a-930c-405c-8c00-eceee4caf12f gen_ai.operation.name=surface gen_ai.request.model=voyage-4 gen_ai.usage.input_tokens=24 gen_ai.usage.output_tokens=0 gen_ai.response.finish_reasons=success cost.usd=1.4399999999999998e-6 latency.ms=244
---------- ToolCallExecutionEvent (Data_Discovery_Agent) ----------
[FunctionExecutionResult(content='{"fail_open":false,"latency_ms":242,"surfaced":[]}', name='surface', call_id='call_93o89w7b', is_error=False)]
```

Telemetry for that invocation — note `voyage-4`, see divergence 1:

```
2026-09-27T15:37:20.576875Z  INFO serve_inner: mcp_parallax::telemetry: invocation recorded invocation.id=aeeeff07-526d-4d41-9a68-4bd04370592f session.id=c20e2a3a-930c-405c-8c00-eceee4caf12f gen_ai.operation.name=surface gen_ai.request.model=voyage-4 gen_ai.usage.input_tokens=24 gen_ai.usage.output_tokens=0 gen_ai.response.finish_reasons=success cost.usd=1.4399999999999998e-6 latency.ms=244
```

Final report extract — concrete indices/fields, and the agent states plainly that
the memory tool came up empty:

```
|Index/DataSource| Type of Data | Key Fields|
|----------------|-------------|----------|
|WinASOS_events| Windows Security Event Logs| Event ID (4688, 6), Logon SID, User ID, Process Creation Details, PSCommand|
|Security| Windows Security Event Logs| Event ID (4688, 6), Logon SID, User ID, Process Creation Details, PSCommand|
|Sysmon| Detailed Process and Network Monitoring| Process ID, Process Name, Parent Process ID, Command Line, User ID, Event ID (4688, 103)|

The "Surface" tool did not return any relevant memories; however, the Windows Security logs and Sysmon logs could potentially provide the necessary evidence to test the hypothesis. The Process Creation logs (Event ID 4688) and WinRM session establishment logs (Event ID 6) from both the `WinASOS_events` and `Security` indices would be particularly useful. The `Sysmon` index may also contain additional details about process creation and network activities. The key fields `PSCommand`, `Process Name`, and `Command Line` are especially relevant for detecting PowerShell usage and lateral movement.
```

Critic termination — the RoundRobinGroupChat ended on the expected sentinel:

```
**YYY-TERMINATE-YYY**
```

CLI invocation (`-a`/`-c` are file paths — divergence 3):

```
uv run python -m peak_assistant.data_assistant -y "The attacker used PowerShell for
lateral movement inside the victim network." -r <research.md> -a <able.md> -c <context.md> -v --no-feedback
```

## 3. Divergence list (feeds the bug lists)

1. **RESOLVED 2026-09-27 (strict-keyless rerun)** — PEAK merges the parent
   environment into spawned MCP servers (`mcp_config.py`:
   `os.environ.copy()` then `update(config.env)` — the block can override but
   not delete). Shell keys (`VOYAGE_API_KEY`, `BRAVE_API_KEY`, `ANTHROPIC_API_KEY`,
   `OPENAI_API_KEY` — all set in the demo shell) therefore leaked into parallax
   despite the `env` block; in the original M2 run `surface` made a real voyage-4
   embedding call (`gen_ai.request.model=voyage-4`, `cost.usd=1.44e-6`). The scrub
   pattern that closes it: set each key to the empty string in the `env` block —
   parallax normalizes blank keys to absent, so the override neutralizes the
   leak. Verified: rerun with the scrub (`notes/m2-keyless-rerun-transcript.log`,
   exit 0) shows **zero voyage/brave/anthropic/openai.com markers**, no `surface`
   call, and the one tool invocation attributing to `qwen2.5:7b`.
2. **RESOLVED 2026-09-27** — parallax routing log mislabeled the source: it printed
   `source=ANTHROPIC_MODEL` although the model resolved from `OPENAI_MODEL` with
   `backend="openai_compat"`. Fixed by parallax PR #109 (merged `5df9656`, all 8
   checks green): `RouteSource::Default` now records the backend's real default
   variable. Verified live — the startup table now prints
   `source=OPENAI_MODEL` on the Ollama backend.
   **Follow-up 2026-09-28 (#112):** the corrected label stayed correct-but-cryptic —
   `source=OPENAI_MODEL` names the *variable* that supplied the model, but with
   `OPENAI_API_BASE=http://localhost:11434/v1` the vendor-suggestive spelling made the
   line read as OpenAI-bound on a fully local run (operator query: "I am not using
   openai"). parallax PR #112 (merged `2e5b4c0`) adds `endpoint=` to every routing
   line, read from the same config the client was built against:
   `source=OPENAI_MODEL endpoint=http://localhost:11434/v1`. Verified live on the
   rebuilt binary.
3. **RESOLVED 2026-09-27** — PEAK CLI `-a`/`-c` (and planning's `-d`) are file paths,
   not inline text, despite help text implying inline values. Fixed by aligning the
   help text across all four CLIs (`data_assistant`, `planning_assistant`,
   `able_assistant`, `hypothesis_refiner`) — "Path to the ... file" — pinned by
   `tests/unit_tests/test_cli_help_path_parity.py` (8 tests), fork PR #21
   (merged `b062dc1`). Inline-value support
   was considered and rejected: a typo'd path silently becoming literal content is
   worse than a loud "file not found".
4. **Positive:** qwen2.5:7b (7B, local) held the full agent+critic loop — one real
   function call, a coherent index report, and correct `YYY-TERMINATE-YYY` termination
   with no `max_turns` set. The provider-agnostic seam works against a small local model.

Carried-over issues unrelated to the backend swap: `previous_run` tool-role bug (fixed
in fork PR #9), `is_capability_rejection` broad-token risk, rustls 0.23.43 version cap
unexplained, live smoke inherits the 2s `test_config` timeout (latent flake).

## 4. Exit-criteria mapping

> Exit criteria: reproducible demo on a clean PEAK checkout with only
> `mcp_servers.json` + env added.

Met 2026-09-27. No PEAK source file was modified; the whole integration is the two
config files in section 1. Prerequisites are environment, not code:

1. a built parallax binary (`cargo +1.98.0 build` in the parallax fork at `e7f12f8`)
   at the path in `command`;
2. Ollama running with `qwen2.5:7b` pulled (4.7 GB);
3. `model_config.json` pointing the active provider at the local endpoint —
   `ollama-local` ships as an example; the `qwen2.5:7b` model entry with
   `function_calling`/`structured_output` flags was added here.

Caveat vs a strictly "clean" checkout: the binary path and the model entry are
machine-specific; a released parallax binary plus a documented model entry would
shrink the delta to two config edits.

---

Prepared on `notes/research`. The gitignored originals (`mcp_servers.json`,
`model_config.json`) remain uncommitted; only these quoted snippets and the verbatim
transcript land.
