# PEAK × mcp-parallax — Research Notes

**Status:** verified against local source on 2026-09-26 (all claims read in code; see Sources).
**Confidence convention:** *[verified]* = read in source (path given); *[inferred]* =
reasoning from verified facts; *[TODO]* = could not confirm. Corrections to the
carried-over brief are marked **Correction** inline and collected near the end.

---

## 1. Context / Goal

PEAK-Assistant (Cisco-Talos) is a hypothesis-driven threat-hunting assistant.
mcp-parallax (`quanticsoul4772/mcp-parallax`) is a Rust MCP server of
"correctives" for predictable LLM failure modes (verification, unblocking,
divergent thinking, decision support, deterministic checking, memory).
Goal of this research: determine, with evidence, what it would take to use
parallax as an **opt-in verification layer** inside PEAK's hypothesis phase,
and what it would take to make parallax provider-agnostic (BYOM) so PEAK's
model configuration philosophy carries over.

---

## 2. PEAK-Assistant overview *(all verified)*

### 2.1 Workflow (README.md "Workflow" section)

1. Research Phase — public Internet sources
2. Local Research Phase — internal sources (tickets, wikis, threat intel)
3. Hypothesis Generation
4. Hypothesis Refinement
5. ABLE Table Creation (Actor, Behavior, Location, Evidence)
6. Data Discovery (SIEM, e.g. Splunk)
7. Hunt Planning

(Matches the carried-over claim; README numbering itself has a duplicate "2." — cosmetic.)

### 2.2 Architecture

- Python ≥3.12, AutoGen (`autogen`, `autogen-agentchat`, `autogen-ext`), Streamlit UI,
  `mcp` + `autogen_ext.tools.mcp` (`McpWorkbench`, `StdioServerParams`) for MCP
  (pyproject.toml).
- Package layout: `peak_assistant/{research_assistant, hypothesis_assistant,
  able_assistant, data_assistant, planning_assistant, streamlit, utils, mcp_status,
  peak_mcp}` (the last exposes PEAK's own phases as MCP tools — noted in §7).
- Multi-agent AutoGen with explicit critic reviewers *(verified)*:
  - `summary_critic`, `hunt_plan_critic`, `Discovery_Critic_Agent`,
    `hypothesis-refiner-critic` (MODEL_CONFIGURATION.md agent table, lines 110–125).
  - Critics are plain `AssistantAgent`s inside `RoundRobinGroupChat` teams with a
    `TextMentionTermination` sentinel: `"YYY-HYPOTHESIS-ACCEPTED-YYY"` in the
    hypothesis refiner (`hypothesis_refiner_cli.py:323`), `"YYY-TERMINATE-YYY"`
    in data discovery (`data_assistant/__init__.py:227–243`).

### 2.3 Hypothesis phase — actual code (replaces all guessed paths)

| Claimed name | Reality *(verified)* |
|---|---|
| `hypothesizer_agent` | `peak_assistant/hypothesis_assistant/hypothesis_assistant_cli.py`, `async def hypothesizer` (line 36). Uses `get_model_client(agent_name="hypothesizer_agent")` (line 175) and calls `client.create(messages)` **directly** (line 179) — no `AssistantAgent`, no team, no MCP tools. |
| `hypothesis-refiner` | `peak_assistant/hypothesis_assistant/hypothesis_refiner_cli.py`, `AssistantAgent("refiner", ...)` (line 313); client `get_model_client(agent_name="hypothesis-refiner")` (line 309). |
| `hypothesis-refiner-critic` | Same file, `AssistantAgent("critic", ...)` (line 318); client `get_model_client(agent_name="hypothesis-refiner-critic")` (line 310). |

Critic wiring *(verified, `hypothesis_refiner_cli.py:308–360`)*:

```python
text_termination = TextMentionTermination("YYY-HYPOTHESIS-ACCEPTED-YYY")  # line 323
team = RoundRobinGroupChat(
    [critic_agent, refiner_agent], termination_condition=text_termination
)
```

The critic's system prompt (line 118–119) is freeform: *"Evaluate this hypothesis
against 8 quality criteria and provide specific, actionable feedback for
improvement. Do NOT rewrite the hypothesis."* No structured output, no
checkable contract. **The "key gap" claim (critics = freeform prose) is
confirmed.**

**Important finding:** the hypothesis agents carry **no MCP plumbing at all** —
no `mcp_config` imports, no workbench parameters (grep of
`hypothesis_assistant/*.py`). Only the research and data-discovery assistants
use `setup_mcp_servers(...)` + `McpWorkbench`. This decides the config-vs-code
question (§6).

### 2.4 MCP groups and `mcp_servers.json`

- **Correction/clarification:** `mcp_servers.json` is **not shipped** in the repo.
  It is user-created; `_find_config_file` (`utils/mcp_config.py:588–608`) searches
  `mcp_servers.json`, `../mcp_servers.json`, `.mcp_servers.json`,
  `~/.config/peak-assistant/mcp_servers.json`, `/etc/peak-assistant/mcp_servers.json`.
  (The code copies `mcp_servers.json.example` if present, but that example file is
  not in the repo either; README embeds a template instead.)
- Schema *(verified, `mcp_config.py:_load_config` lines 620–720 + README template)*:
  `{"mcpServers": {name: {transport, command, args, env, url, auth, description, timeout}},
  "serverGroups": {group: [server names]}}` (also accepts a `"servers"` array).
  `${ENV_VAR|default}` interpolation applies (`_interpolate_env` → shared
  `interpolate_env_vars`).
- Groups actually used *(verified)*: `research-external`
  (research_assistant/__init__.py:43), `local-data-search`
  (research_assistant/__init__.py:401), `data_discovery`
  (data_assistant/__init__.py:44). Confirms the carried-over list.

### 2.5 BYOM — `model_config.json` *(verified: MODEL_CONFIGURATION.md + utils/model_config_loader.py + utils/llm_factory.py)*

- Top level: `version`, `providers`, `defaults`, `groups` (wildcard `match` via
  fnmatch), `agents`.
- **Precedence:** `agents.<name>` (exact) → first matching `groups.*` (glob) →
  `defaults` (model_config_loader.py:121–165).
- Provider types: `azure`, `openai`, `anthropic` (llm_factory.py:150–158).
  OpenAI-compatible/local servers (Ollama, vLLM, LM Studio) via `base_url` +
  `model_info`; Anthropic supports `base_url` (proxies); Azure supports
  `auth_module` custom auth (CUSTOM_AUTHENTICATION.md).
- `${ENV_VAR}` / `${ENV_VAR|default}` / `${ENV_VAR|null}` interpolation.
- Carried-over BYOM claim: **confirmed in full.**

### 2.6 Tests / tooling *(verified: Makefile, pyproject.toml, tests/)*

- pytest + pytest-asyncio (`asyncio_mode = "auto"`), ruff, mypy,
  `@pytest.mark.live` marker (registered in pyproject; used in
  `tests/integration/test_live_all_providers.py`, `test_live_optional_params.py`).
- **Correction:** `make checks` runs **ruff + mypy only** — it does not run pytest.
  `make coverage` runs `coverage run -m pytest`. So "make checks / make coverage"
  exists, but `checks` ≠ tests.

---

## 3. mcp-parallax overview *(all verified; tree read dirty, see Sources)*

### 3.1 Stack

Rust (edition 2021, rust-version 1.94), `#![forbid(unsafe_code)]` (src/lib.rs:28;
Cargo.toml lint `unsafe_code = "forbid"` line 97), rmcp MCP SDK, tokio,
sqlx/SQLite (Cargo.toml:47), z3 0.20 **bundled** + evalexpr 13 (Cargo.toml:54–55),
Voyage AI embeddings (src/client/voyage.rs), Brave Search (src/client/brave.rs).
Confirms the carried-over stack claim.

### 3.2 Tool catalog — 15 tools *(verified from `#[tool(name = ...)]` in src/server.rs)*

`verify`, `unstick`, `diverge`, `decide`, `elicit`, `save`, `recall`, `forget`,
`surface`, `research`, `grounded_verify`, `check`, `checkpoint_action`,
`checkpoint_batch`, `checkpoint_turn`. Exactly matches the brief.
Gating *(verified, server.rs:104–112)*: memory tools (`save`/`recall`/`forget`/`surface`)
are **absent** from the catalog without `VOYAGE_API_KEY`; `grounded_verify` is
**absent** without `GROUNDED_VERIFY_ROOT`.

### 3.3 Tool I/O schemas *(verified from contract/mode structs)*

| Tool | Input | Output |
|------|-------|--------|
| `verify` | `VerifyParams { claim, context?, effort?: Effort, passes?: u8 }` (modes/verify.rs:102) | `Verdict { verdict: supported\|refuted, findings, confidence (server-computed agreement ratio), passes }` wrapped in `VerifyRun` (modes/verify.rs:155–182) |
| `unstick` | `UnstickParams { goal, blocked (default), tried?: Vec<String>, effort? }` (modes/unstick.rs:50) | `UnstickRun { step: NextStep, tokens }` (modes/unstick.rs:117) |
| `diverge` | `DivergeParams { problem, context?, effort?, ... }` (modes/diverge.rs:118) | `DivergeResult { perspectives: Vec<Perspective>, passes }` (modes/diverge.rs:175) |
| `decide` | `DecideParams { decision, options: Vec<String>, options_text?, context?, effort? }` (modes/decide.rs:78) | `DecideResult { recommended, runner_up, runner_up_reason, confidence, methodology }` (modes/decide.rs:151) |
| `elicit` | `ElicitParams { task, context?, effort? }` (modes/elicit.rs:84) | `ElicitResult { assumed_objective, governing_preferences, divergence_points, signal_level, memory_consulted }` (modes/elicit.rs:145) |
| `check` | `CheckParams { claim, context?, effort? }` (deterministic/contract.rs:13) | `CheckResult { verdict: supported\|refuted\|not_checkable, engine, formal_form, engine_result, witness, explanation, reason?, translation_attempts }` (contract.rs:32) |
| `grounded_verify` | `GroundedVerifyParams { claim, locators: Vec<SourceLocator>, ... }` (modes/grounded_verify.rs:123) | aggregated `Verdict` (shares `aggregate_core` with `verify` — modes/verify.rs:166 comment) |
| `save` | `SaveParams { content, kind: Kind, origin }` | `SaveResult` |
| `recall` | `RecallParams { query, kind?, limit? }` | `RecallResult` (embedding similarity) |
| `forget` | `ForgetParams { id }` | `ForgetResult` |
| `surface` | `SurfaceParams { session_id, prompt }` | `SurfaceResult` (push-style recall) |
| `research` | `ResearchParams { question, depth?: Depth, focus?: Vec<String>, ... }` (research/contract.rs:16) | multi-phase research report with per-claim verdicts |
| `checkpoint_*` | `CheckpointActionParams` / `CheckpointBatchParams` / `CheckpointTurnParams` — each `{ session_id, transcript_path, ... }` (checkpoint/contract.rs:14–46) | `CheckpointResult` (contract.rs:132) |

`check` is deterministic-first: an LLM translates the claim to a formal form
(`CHECK_TRANSLATE`), then Z3/evalexpr decide it (engines), with a violation-fed
retry (`translation_attempts` 1–2). Server-assembled `explanation` is never
model-phrased (contract.rs doc comment).

### 3.4 Config surface *(verified: src/config.rs:175 `Config::from_env`)*

Confirmed as claimed: `ANTHROPIC_API_KEY` (**required** — `ConfigError::MissingRequired`),
`ANTHROPIC_MODEL`, `ANTHROPIC_API_BASE`, `VERIFY_ENSEMBLE_K` (default 3),
`VOYAGE_API_KEY`, `BRAVE_API_KEY`, `GROUNDED_VERIFY_ROOT`, `DATABASE_PATH`
(default `./data/parallax.db`), `LOG_LEVEL`, plus `PARALLAX_MODEL_*` /
`PARALLAX_EFFORT_*` per call site and tier (routing.rs:44–46).

**Extension (list was incomplete):** also `DIVERGE_PASSES`, `INPUT_MAX_CHARS` /
`VERIFY_MAX_CLAIM_CHARS` (50,000), `VOYAGE_MODEL`, `MEMORY_RECALL_LIMIT` (5),
`FETCH_TIMEOUT_MS` (10s), `RESEARCH_CONCURRENCY` (8), `FETCH_ALLOW_PRIVATE`,
`CHECKPOINT_GATE_PATTERNS`, `GROUNDED_VERIFY_MAX_BYTES`,
`GROUNDED_VERIFY_MAX_LOCATORS`, `REQUEST_TIMEOUT_MS` (120s), `MAX_RETRIES` (3).

Routing resolution *(verified, routing.rs:13–14 doc + `RoutingTable::resolve`)*:
effort comes from configured level, else `PARALLAX_EFFORT_<SITE>`, else
`PARALLAX_EFFORT_<TIER>`; model from `PARALLAX_MODEL_<SITE|TIER>` else
`ANTHROPIC_MODEL`. Unknown `PARALLAX_MODEL_*` suffixes fail startup.

### 3.5 Model coupling — the core finding

**Correction to "thin `ModelClient::complete` wrapper":** the seam already exists
as a first-class trait *(verified, src/traits/client.rs:26)*:

```rust
#[cfg_attr(test, mockall::automock)]
#[async_trait::async_trait]
pub trait ModelClient: Send + Sync {
    async fn complete(&self, prompt: &str, schema: &Value) -> Result<Completion, AppError>;
}
```

`Completion { value, input_tokens, output_tokens }`. Tests already use
`MockModelClient` (mockall). So BYOM is an **adapter-implementation** task, not
an extraction refactor.

The Anthropic-only wire format lives entirely in `src/client/anthropic.rs`
*(verified)*:

- `impl ModelClient for AnthropicClient` (line 259); `complete` builds
  `POST {base_url}/v1/messages` (line 237) with `anthropic-version` header (239).
- Body uses `output_config.format = {type: "json_schema", schema}` (line 264);
  routed `effort` joins under `output_config` (lines 261–272); `max_tokens` set.
- `stop_reason` checked before the body is trusted (lines 334–370):
  `end_turn` → ok; `max_tokens` → `AppError::Truncation` **with billed tokens**;
  anything else → out-of-contract `Client` error.

**Verdict:** "hard-coupled to Anthropic wire format" = **confirmed**. The single
production impl is `AnthropicClient`; everything else is test mocks.

### 3.6 Call sites — "12" confirmed, with two nuances

`CallSite` enum (src/routing.rs:150–178) with `ALL: [Self; 12]` is exactly the
brief's list: Verify, Unstick, Diverge, Decide, Elicit, GroundedVerify,
CheckTranslate, ResearchScope, ResearchExtract, ResearchVerify,
ResearchSynthesize, CheckpointReview. **Confirmed** — and this is the authoritative
routable set ("the complete routable set", data-model.md §1).

Physical `.complete()` call sites in production code (12 total):

| Physical site | Routed call site(s) |
|---|---|
| `src/modes/verify.rs:285` | VERIFY **and** RESEARCH_VERIFY (shared `verify::run`; RESEARCH_VERIFY passes `pool.for_site(CallSite::ResearchVerify)` — server.rs:331, pipeline.rs:672–676) |
| `src/modes/unstick.rs:224` | UNSTICK |
| `src/modes/diverge.rs:289` | DIVERGE |
| `src/modes/decide.rs:303` | DECIDE |
| `src/modes/elicit.rs:337` | ELICIT |
| `src/modes/grounded_verify.rs:331` | GROUNDED_VERIFY |
| `src/deterministic/translate.rs:194` | CHECK_TRANSLATE |
| `src/research/pipeline.rs:500` | RESEARCH_SCOPE |
| `src/research/extract.rs:84` | RESEARCH_EXTRACT |
| `src/research/synthesis.rs:168` | RESEARCH_SYNTHESIZE |
| `src/checkpoint/review.rs:366` | CHECKPOINT_REVIEW |
| `src/memory/consolidate.rs:239` | *(none — memory consolidation)* |

**Nuance 1:** RESEARCH_VERIFY does not have its own `.complete()`; it reuses
`verify::run` with its own routed client. **Nuance 2:** memory consolidation
(`memory/consolidate.rs:239`, the "keep-both-or-merge" judge) has no `CallSite`
of its own — it borrows `pool.for_site(CallSite::Verify)` (server.rs:315).
**Counting:** 12 routed operations map onto 11 physical `.complete()` sites
(verify.rs serves two), and consolidation adds one unrouted physical site —
**12 physical sites, 13 LLM-backed operations total**. A migration plan must
cover consolidation even though the routed count stays 12.

---

## 4. mcp-reasoning brief (out of scope; spot-checked) *(verified)*

README claims 35 tools; **count confirmed** (35 `name = "reasoning_*"` tool
registrations in src/). Category claims confirmed: linear/tree/MCTS
(`reasoning_linear`, `reasoning_tree`, `reasoning_mcts`), TOPSIS decision
(`reasoning_decision`), semantic memory via Voyage (`reasoning_search`,
`reasoning_relate`).

**Corrections — three tool names in the brief do not exist:**
- `reasoning_assess_evidence` → actual: **`reasoning_evidence`**
- `reasoning_detect_fallacies` → actual: **`reasoning_detect`** (biases + fallacies)
- "GoT" → actual: **`reasoning_graph`**

Also present: `reasoning_counterfactual`, `reasoning_reflection`,
`reasoning_confidence_route`, `reasoning_si_*` (self-improvement loop),
`reasoning_agent_*`/`reasoning_crew_invoke`/`reasoning_team_*` (coordination).
Do not design for this repo now.

---

## 5. parallax → PEAK phase mapping *(inferred from verified facts)*

| PEAK phase | parallax tool(s) | Fit |
|---|---|---|
| Research (external/local) | `research` | Overlaps PEAK's own research teams — see §7. Advisory use only. |
| Hypothesis Generation | `diverge` (frame alternatives), `elicit` (missing requirements) | Candidate for opt-in quality prompts. |
| Hypothesis Refinement (critic) | **`verify`** (advisory), **`grounded_verify`** (claim-vs-artifact) | Primary integration target (Doc 3). |
| ABLE Table | `check` (consistency of quantitative claims) | Optional later. |
| Data Discovery | `check` (deterministic sanity of field/index claims) | Weak fit; skip initially. |
| Hunt Planning | `decide` (plan-branch choice), `checkpoint_*` (turn review) | Optional later. |
| Cross-cutting | `save`/`recall`/`surface` (memory), `unstick` | See §7 overlap notes. |

---

## 6. Code-level coupling findings (the config-vs-code question) *(verified)*

**Q: Can `mcp_servers.json` add a new MCP server group with NO code change?**

**A: Split answer.**

1. *Adding a server to an **existing** group* (`research-external`,
   `local-data-search`, `data_discovery`) is **config-only**: add the entry under
   `mcpServers`, append its name to the group list in `serverGroups`. Agents
   connect whatever the group contains (`setup_mcp_servers(group)` →
   `MCPClientManager.connect_server_group`).
2. *Mapping a **new** group to a specific agent* **requires a code change**: the
   group→agent mapping is hardcoded as Python function parameter defaults
   (`mcp_server_group_external: str = "research-external"` etc.; no CLI flag, no
   config key). `serverGroups` in JSON defines groups freely, but nothing routes
   a new group to an agent without touching call sites.
3. *The hypothesis phase has no MCP support whatsoever* (§2.3): even attaching an
   existing group to the hypothesis critic is a **code PR** (new workbench
   plumbing + tool plumbing into `AssistantAgent(..., workbench=...)`).

**Consequence for the first integration:** a zero-PEAK-code demo is possible by
registering parallax inside an existing group (M2 in roadmap), but the actual
target integration (hypothesis critic with `verify`/`grounded_verify`) is a code
PR (M4). This should be stated openly in the PEAK issue (Doc 3).

---

## 7. Overlap notes *(inferred)*

- **parallax `research` vs PEAK external search:** parallax's `research` tool has
  its own fetch/search stack (Brave, `FETCH_*` config, source credibility,
  per-claim verify). PEAK's research phase uses user-supplied MCP search servers
  (e.g. Tavily) + AutoGen teams. These would duplicate if both run in the same
  phase. Recommendation: keep PEAK's research as-is; use parallax `research` only
  as an independent *second pass* (that's the heterogeneous-verification value),
  never as a replacement.
- **parallax memory vs mcp-reasoning memory:** parallax has SQLite + Voyage
  embedding memory (`save`/`recall`/`forget`/`surface`, consolidation judge);
  mcp-reasoning has session memory (`reasoning_search`/`reasoning_relate`, also
  Voyage). Both are optional, both gate on `VOYAGE_API_KEY`. They are separate
  stores; no shared schema *(verified: distinct crates/storage)*. If both are ever
  attached to PEAK, memory tools should live in **one** group only to avoid two
  competing stores answering "what do we already know".
- **PEAK runs its own MCP server** (`peak_mcp/__main__.py`, `@mcp.tool` entries
  like `internet_researcher`, `hypothesizer`, `hypothesis_refiner`,
  `able_table`, `data_discovery`). Interesting future option: parallax could be
  layered at that boundary instead — noted as an open question.

---

## 8. Corrections summary

1. **`ModelClient` is already a trait** (`src/traits/client.rs:26`, with mockall
   automock), not a thin wrapper needing extraction. BYOM = second impl.
2. **"12 call sites" confirmed** at the routing level (`CallSite::ALL`, exact
   names), but the physical map has 12 `.complete()` sites covering **13
   LLM-backed operations**: RESEARCH_VERIFY shares `verify::run`, and memory
   consolidation (unrouted) borrows the Verify client.
3. **parallax env-var list incomplete** — see §3.4 for the full set.
4. **`make checks` = ruff + mypy only**, not tests (`make coverage` runs pytest).
5. **mcp-reasoning tool names corrected**: `reasoning_evidence`, `reasoning_detect`,
   `reasoning_graph` (not `reasoning_assess_evidence` / `reasoning_detect_fallacies` / "GoT").
6. **`mcp_servers.json` is not in the repo** and `mcp_servers.json.example`
   referenced by code doesn't exist either; README template is the spec.
7. **Hypothesis agents have zero MCP plumbing** — "new group mapped to the
   hypothesis critic" is a code PR, not config-only (decisive for Doc 3).
8. **Provenance caveat:** both MCP checkouts are on feature branches
   (`053-diverge-pass-count` dirty ×13 files; `fix/retired-sonnet4-default`
   clean), not `main`. Findings describe the working tree as read.

## 9. Open Questions

1. Will PEAK maintainers accept *any* extra model calls in the hypothesis phase
   if opt-in and off by default? (Doc 3 Q1.)
2. Config-only demo (existing group) vs code PR (critic mapping) — which does
   upstream prefer as a first contribution? (Doc 3 Q2.)
3. Should `verify` runs inside PEAK use a *different provider* than the PEAK
   agents by design (heterogeneous verification), and how is that expressed in
   `model_config.json` + parallax's own env config without credential passthrough
   through tool arguments?
4. parallax `verify` confidence is derived from cross-pass agreement — do we
   surface ensemble size (`VERIFY_ENSEMBLE_K`) to PEAK users in the UI or treat
   it as deployment config?
5. When parallax's structured-output fidelity differs across providers (Doc 2
   risks), which errors are acceptable to bubble to a threat hunt workflow?

---

## 10. Sources (commit SHAs and dates)

| Repo | Path | HEAD | Commit date | Branch / state |
|------|------|------|-------------|----------------|
| PEAK-Assistant (fork) | `D:\Projects\PEAK-Assistant` | `dfabbb0fbcc27292ecbb8e32beeccda372bc0783` | 2026-06-01 | `notes/research` (cut from `upstream/main`); clean |
| mcp-parallax | `C:\Development\Projects\MCP\project-root\mcp-servers\mcp-parallax` | `a539aacc49ae6e0b5f21fd33a2cda856c223da29` | 2026-07-28 | `053-diverge-pass-count`; **dirty (13 files)** |
| mcp-reasoning | `C:\Development\Projects\MCP\project-root\mcp-servers\mcp-reasoning` | `678d7112a3cc30c846fc51ace64c3ca3e97d5186` | 2026-09-09 | `fix/retired-sonnet4-default`; clean |

Provenance captured 2026-09-26T11:59:34-07:00. mcp-parallax dirty files: `CHANGELOG.md`,
`CLAUDE.md`, `README.md`, `examples/common/mod.rs`, `specs/012-diverge-perspectives/*`
(3 files), `src/config.rs`, `src/main.rs`, `src/modes/diverge.rs`, `src/modes/mod.rs`,
`src/server.rs`, `tests/integration.rs` — read as-is, nothing stashed or modified.

Key files cited: PEAK `README.md`, `MODEL_CONFIGURATION.md`, `CUSTOM_AUTHENTICATION.md`,
`Makefile`, `pyproject.toml`, `peak_assistant/utils/{mcp_config,model_config_loader,llm_factory}.py`,
`peak_assistant/hypothesis_assistant/{hypothesis_assistant_cli,hypothesis_refiner_cli}.py`,
`peak_assistant/{research_assistant,data_assistant}/__init__.py`;
parallax `src/{config,routing,server}.rs`, `src/traits/client.rs`,
`src/client/anthropic.rs`, `src/modes/*.rs`, `src/research/{contract,pipeline,extract,synthesis}.rs`,
`src/{deterministic,checkpoint,memory}/{contract,review,consolidate,translate}.rs`, `Cargo.toml`.
