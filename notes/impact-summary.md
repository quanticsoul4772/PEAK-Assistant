# Impact analysis: parallax + MCP improvements on PEAK

Date: 2026-09-29. Every claim below is backed by a measurement from this
session — A/B comparisons against real pre-fix commits (checked out into
throwaway worktrees), live runs against the Splunk trial container, or the
20-run experiment in `notes/7b-variance.md`.

## 1. What parallax contributes to PEAK functionally

Without the parallax fork work, PEAK's MCP surface would be search + Splunk
only. With it:

- **Corrective memory inside PEAK's hunts**: `grounded_verify`, `verify`,
  `remember`, `recall` etc. reach PEAK agents through the
  `hypothesis-verification` group (M4 wiring) and `data_discovery`.
  PR #107/#108 are what make that run on a keyless local Ollama backend —
  an anthropic-only parallax would have made the PEAK×parallax integration
  a non-starter for local hunts.
- **A second discovery model option**: the 20-run experiment showed
  llama3.1:8b executes real SPL in 6/10 runs vs qwen2.5:7b's 1/10. That
  option exists because #107–#112 made parallax model-agnostic; #112's
  `endpoint=` routing line is what proved localhost-only operation during
  the egress checks.

## 2. parallax reliability fixes and their effect on PEAK runs

| parallax fix | PEAK experience before | Now |
|---|---|---|
| #111 Effort case fix | M4 critic runs died on `"effort":"Medium"` from PEAK's 7B | verdicts return |
| #113 capability-rejection fix (A/B-verified) | auth failure phrased "unsupported auth scheme" → 4 wasted ladder attempts on a dead key → PEAK saw a confusing "strategy rejected" error instead of the auth problem | fails loud, names the real cause, zero burned retries; `"unknown tool"` config mistakes no longer hide as capability signals |
| #114 smoke timeout | the opt-in live smoke used to sanity-check PEAK×parallax integration inherited a 2 s timeout and flaked on slow hardware | production 120 s |

## 3. MCP-side fixes in PEAK, measured (A/B against pre-fix commits)

| Fix | OLD (pre-fix commit) | NEW (main) |
|---|---|---|
| #38 agent-config shadowing (`{"hunt_planner": {}}`) | `ModelConfigError: No 'provider' field found` — startup dead | resolves `{provider: ollama-local, model: qwen2.5:7b}` from defaults |
| #39/#40 env scoping (bait keys exported in parent shell) | spawned parallax child received **119 env keys** incl. `VOYAGE_API_KEY=bait-222`, `BRAVE_API_KEY=bait-333`, and un-listed `EXA_API_KEY=leak-444` | **18 keys** (allowlist + config), zero secret-bearing; bait never arrives |
| #32–#35 grounding enforcement (pre-#33 code `153cf31`) | 3 of today's 4 pinned warning/hard-fail tests fail against it; no remedies printed, no `exit(1)` | 16/16 grounding tests pass; `GROUNDING ERROR` + remedies + `--allow-ungrounded-plan` |
| #37 hybrid CLI flags | inline values impossible | inline ABLE/context verified reaching the model end-to-end; path-shaped typos still fail loudly |

## 4. Grounding under model variance (20-run live experiment)

At 7B, tool usage is stochastic — that part is inherent to the models. What
the enforcement chain changed is the *consequence* of that variance:

- 20/20 runs (both models) cite only `winrm_hunt`; **zero fabricated index
  names**; `UNVERIFIED` warning silent (search-capable group present). The
  original finding-10 run had 4 fabricated indices and invalid SPL approved
  by the critic.
- 20/20 clean `YYY-TERMINATE-YYY` terminations.
- Variance now costs depth (qwen: 9/10 tool calls but 1/10 executed real
  SPL; llama: 10/10 tool calls, 6/10 real SPL), not grounding.

## 5. Current state

- PEAK fork `main` `615cf87` — PRs #9–#41 merged. Ledger: findings 1, 3, 9,
  10 resolved and implemented; sole open item is upstream engagement
  (gated on an explicit human decision).
- parallax fork `main` `62ef1bd` — PRs #107–#114 merged; hygiene item
  closed (#113, #114; the "rustls cap" was never our pin — lockfile resolves
  0.23.45 via reqwest 0.13.5).
- Local gitignored configs: both parallax blocks run `inheritEnvironment:
  false` with null-removed key stubs; `model_config.json` on qwen default
  with llama `model_info` available.
- Suites: PEAK 308 passed +1 skipped, ruff/mypy clean; parallax 545+24+72
  passed, clippy at pre-existing warnings.
