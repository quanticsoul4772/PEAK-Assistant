# M4 implementation plan — opt-in hypothesis-verification group (D1)

Status: plan (2026-09-27), pre-implementation. Implements memo decisions D1/D2/D3/D4/D5;
fork-only PR per roadmap M4. Branch: `feat/hypothesis-verification-group` cut from fresh `main`.

## 1. Survey findings (verified against fork main `1a07a82`)

- **The critic is bare today.** `hypothesis_refiner_cli.py` builds
  `critic_agent = AssistantAgent("critic", model_client=..., system_message=critic_system_prompt)`
  (line ~318) with **no workbench**; team = `RoundRobinGroupChat([critic_agent, refiner_agent],`
  `termination_condition=TextMentionTermination("YYY-HYPOTHESIS-ACCEPTED-YYY"))`.
- **Call sites of `refiner()`** (all pass only documented args, none touch MCP):
  CLI `main()` loop (`hypothesis_refiner_cli.py:498`), streamlit (`streamlit/util/runners.py:174`),
  `peak_mcp` (`peak_mcp/__main__.py:337`, wraps `async_refiner`).
- **Established wiring pattern** (`data_assistant/__init__.py`):
  `setup_mcp_servers(group)` -> `mcp_client_manager.get_workbench(server_name)` ->
  `AssistantAgent(..., workbench=mcp_workbench, reflect_on_tool_use=True)`.
- **Absent group is a no-op**: `connect_server_group` logs "No servers found in group"
  and returns `[]`; `get_workbench` returns `None`. Nothing raises — ideal for opt-in.
- **Workbench interface** (autogen_ext 0.7.4): `McpWorkbench(Workbench)` with
  `async list_tools() -> List[ToolSchema]`, `async call_tool(name, arguments)`,
  `call_tool_stream`. `AssistantAgent` calls exactly these (`_assistant_agent.py`
  lines 1086/1574/1578/1596) — a delegating filter subclass is sufficient.
- **Gate**: `make checks` = ruff + mypy; pytest under `tests/unit_tests` (+ integration).

## 2. Design (decision D1: one named group in code, one agent)

### 2.1 Group resolution

1. New parameter on `refiner()`: `mcp_server_group: Optional[str] = None`
   (**default `None`, not a group name** — the default path must not even attempt
   an MCP connection, keeping byte-identical behavior per the compatibility table).
2. Helper `_resolve_verification_workbench(group: str, verbose: bool) -> Optional[Workbench]`:
   - `connected = await setup_mcp_servers(group)`; if empty -> log info, return `None`.
   - take the first connected server's workbench via `get_client_manager().get_workbench(...)`;
     `None`/missing -> log info, return `None`.
   - **never raises** (diverges from data_assistant, which raises — that behavior is
     correct for a phase whose whole job is MCP; here MCP is an optional add-on).
3. In `refiner()`: if `mcp_server_group` is None or resolver returns None, construct
   the critic exactly as today; otherwise pass the filtered workbench (2.2).

### 2.2 Tool surfacing: FilteredWorkbench (allowlist)

- Small wrapper in `hypothesis_refiner_cli.py` (or `utils/` if reused later):
  `class _AllowlistWorkbench(Workbench)` delegating to an inner `McpWorkbench`,
  allowlist `{"grounded_verify", "verify"}`:
  - `list_tools()`: filter inner results by allowlist (hides everything else from
    the model — the model cannot call what it cannot see).
  - `call_tool(name, ...)`: raise `ValueError(f"Tool {name!r} is not allowed")` for
    anything outside the allowlist (defense in depth).
  - `call_tool_stream`: same guard, else delegate.
  - `save_state`/`load_state`/`reset` delegate (AssistantAgent may call these).
- Critic gains `workbench=filtered, reflect_on_tool_use=True` **only** when a
  workbench resolved; verdicts stay critic-guidance-only (D3) and termination
  stays `TextMentionTermination("YYY-HYPOTHESIS-ACCEPTED-YYY")` (D4).

### 2.3 Config surface (user-facing, all opt-in)

- `mcp_servers.json` (existing schema, zero changes): user adds a group
  `"hypothesis-verification": ["parallax"]`. mcp-status and mcp-status -v
  already validate groups generically — nothing to add.
- `hypothesis_refiner_cli.py` `main()`: new flag `--verification-group NAME`
  (default: none). When set, passed through to `refiner()`.
- Streamlit / `peak_mcp` callers: **untouched in this PR** (the refiner
  parameter default keeps them working unchanged); wiring them is a follow-up
  if wanted.

## 3. No-default-behavior-change argument (the M4 gate)

With no `--verification-group` / `mcp_server_group=None`: no MCP import path
runs, agents are constructed with the identical kwargs as today, prompts are
untouched, termination unchanged. The only diff on the default path is the
existence of a default-`None` parameter and an `if workbench:` branch that is
never taken. Verified by test T1 (agent construction parity, below).

## 4. Test plan (mocked only; no live calls in CI — memo table row)

New file `tests/unit_tests/test_hypothesis_verification_wiring.py`:

- **T1 default parity**: with group=None, `refiner()` constructs the critic
  without a workbench — assert via monkeypatched `AssistantAgent` capturing
  kwargs; also assert `setup_mcp_servers` is never called.
- **T2 allowlist filtering**: `_AllowlistWorkbench` over a stub inner workbench
  exposing 4 tools -> `list_tools()` returns exactly `grounded_verify`, `verify`
  (schemas preserved).
- **T3 allowlist enforcement**: `call_tool("surface", ...)` raises `ValueError`;
  `call_tool("verify", ...)` delegates to the stub and returns its result.
- **T4 group resolution**: `_resolve_verification_workbench` with
  `setup_mcp_servers` monkeypatched to return `[]` -> returns None (no raise);
  with one connected server -> returns the allowlist-wrapped workbench.
- **T5 opt-in happy path**: group set + stub workbench -> critic kwargs include
  the filtered workbench and `reflect_on_tool_use=True`; refiner kwargs unchanged.
- **T6 CLI flag**: `--verification-group` parses and threads through; default
  run omits it. (argparse-level test, no model calls.)

Runner: `uv run pytest tests/unit_tests/test_hypothesis_verification_wiring.py`
plus full `make checks` (ruff, mypy) and `uv run coverage run -m pytest`.

## 5. Files touched (expected)

| File | Change |
|---|---|
| `peak_assistant/hypothesis_assistant/hypothesis_refiner_cli.py` | `mcp_server_group` param, resolver helper, allowlist wrapper, critic construction branch, CLI flag |
| `tests/unit_tests/test_hypothesis_verification_wiring.py` | new, T1–T6 |
| `README.md` (fork) | short "optional verification group" subsection |
| `notes/roadmap.md` | tick M4 items on merge |

## 6. Risks / notes

- **Workbench ABC surface**: `Workbench` is a pydantic `Component` BaseModel;
  subclassing needs the right `component_config_schema`/`component_type`
  handling. Fallback if awkward: plain composition object implementing the
  4 methods the agent calls (duck-typed), no inheritance — T2/T3 decide.
- `AssistantAgent` with a workbench expects `model_client` to support tool
  calling; users must configure a tool-capable model for the critic when
  opting in (document in README subsection).
- Memory tools inside parallax (`surface`) must NOT be exposed to the critic
  (D5 allowlist covers this — only the two named tools pass).
- Env-inheritance divergence (M2 finding 1) applies here too: document that
  the group env block should scrub keys if strict keyless operation matters.

## 7. PR description skeleton (guarantees from the memo table)

- default path identical (T1); zero extra calls unless opted in; BYOM verifier;
  env-only credentials; no new dependency; mocked tests only; advisory-only
  verdicts (D3/D4); allowlist = exactly {grounded_verify, verify} (D5).
