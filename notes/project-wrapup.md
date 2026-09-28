# Project wrap-up — PEAK × mcp-parallax integration research

Date: 2026-09-27 (single-day arc, M0 through wrap-up). Final states: PEAK fork
`main` at `3d063ef`; parallax fork `main` at `2709859`. Policy held throughout:
zero pushes, PRs, or issues to `Cisco-Talos/PEAK-Assistant`; all work in the
`quanticsoul4772` forks.

## 1. Milestone outcomes (roadmap complete)

| Milestone | Outcome | Provenance |
|---|---|---|
| M0 — verification & workspace | All carried-over claims verified or corrected; provenance recorded; demo environment built | `peak-parallax-research-notes.md`, `deps-audit.md`, `fork-branch-audit.md` |
| M1 — provider-agnostic parallax (BYOM) | `PARALLAX_BACKEND` + `OpenAiCompatClient` with structured-output ladder, error-taxonomy parity, 12 call sites tested offline | parallax PR #107 (`eadda0c`) |
| M1.5 — keyless endpoints | `OPENAI_API_KEY` required only on the default OpenAI endpoint; custom endpoints (Ollama) run keyless; live smoke passed | parallax PR #108 (`e7f12f8`) |
| M2 — zero-PEAK-code demo | `data_discovery` phase ran end-to-end (exit 0) on `qwen2.5:7b`; strict-keyless rerun later proved zero external egress | PR #11 evidence; `m2-demo-evidence.md`, `m2-keyless-rerun-transcript.log` |
| M3 — finalized integration memo | All five design questions resolved as recorded decisions D1–D5; issue shape preserved for possible future upstream filing | PR #12; `peak-integration-issue-draft.md` |
| M4 — first integration PR | Opt-in `hypothesis-verification` group → critic; allowlist {grounded_verify, verify}; never-raising resolver; default path unchanged (pinned by T1) | PEAK fork PR #14 (`8297c13`) |
| M4 — live validation | Steered critic called `verify`, got a `refuted` ensemble verdict from the local model; D3/D4 held | PR #17; `m4-live-validation.md` |

## 2. Divergences found — and how each landed

| # | Finding | Disposition |
|---|---|---|
| 1 | PEAK's env merge (`os.environ.copy()` + `update`) leaks parent-shell credentials into every spawned MCP server; parallax's key-presence features activated (`voyage-4` embedding call in the M2 run) | RESOLVED twice: empty-string scrub demonstrated strict-keyless (config-only); general fix designed as `null`-key removal (`env-merge-design-note.md`, Option B recommended) |
| 2 | parallax routing log printed `source=ANTHROPIC_MODEL` on `openai_compat` | RESOLVED — parallax PR #109 (`DefaultVar`), all 8 CI checks green, live-verified `source=OPENAI_MODEL` |
| 3 | PEAK CLI `-a`/`-c` are file paths despite help text implying inline values | Documented (`m2-demo-evidence.md`); the only open divergence; low priority |
| 4 | Positive: qwen2.5:7b held the full agent+critic loop (real tool call, coherent report, clean `YYY-TERMINATE-YYY`), and in M4 chose the contract-correct tool (`verify` over `grounded_verify`) | Recorded as evidence for the heterogeneous-verification argument |
| 5 | parallax `cost.usd` on local models looked like real spend (Opus-tier fallback pricing) | RESOLVED by decision + PR #110: zeroing declined (endpoint, not backend, decides "free"; cost is observability-only); `cost.estimated` added to the log line, live-verified both success and cancel paths |
| 6 | Small models need steering to use verification tools (unsteered 7B critic never called) | Documented in `m4-live-validation.md`; a prompting concern, not a wiring one |
| 7 | Small models send capitalized effort values (`"effort":"Medium"`); parallax's derived serde impl rejected them exact-match while the env-var path was already case-insensitive | RESOLVED — parallax PR #111 (`a372871`): manual `Deserialize` delegating to `Effort::parse`, schema unchanged (still lowercase), errors still name variants; live-verified `"Medium"` now returns a verdict |
| 8 | Correct-but-cryptic attribution: the post-#109 routing line said `source=OPENAI_MODEL` (true — the env var that supplied the model) while the endpoint was localhost, so a keyless local run read as OpenAI-bound | RESOLVED — parallax PR #112 (`2e5b4c0`): every routing line carries `endpoint=<api base>` from the active backend's config; live-verified `endpoint=http://localhost:11434/v1` beside `source=OPENAI_MODEL` |

Carried-over items that predate this arc and remain open: `is_capability_rejection`
broad-token risk; rustls 0.23.43 version cap unexplained; live smoke inherits the
2s `test_config` timeout (latent flake on slow hardware).

## 3. What a future upstream engagement would need

The memo (`peak-integration-issue-draft.md`) stays issue-shaped so this arc could
be filed to `Cisco-Talos/PEAK-Assistant` **only** on an explicit decision to
engage. If that decision ever comes, the complete checklist is:

1. **The demo is the value story; PR #14 is the code story.** File the issue
   first with the M2/M4 evidence links — never lead with code. The zero-code
   config demo is the strongest possible "works with your existing MCP surface"
   argument and requires no maintainer trust in our review.
2. **Rebase M4 on upstream `main`** and re-check the three call sites the fork
   may have drifted from (`hypothesis_refiner_cli.py`, streamlit `runners.py`,
   `peak_mcp`). The PR was built against fork `1be9a45`; upstream may have moved.
3. **Resolve divergence 3 first** (the `-a`/`-c` file-path quirk) — filing an
   integration proposal whose CLI flags surprise the maintainer invites nit-level
   review before the design discussion even starts.
4. **Carry the compatibility table as the PR contract**: default path byte-identical
   (T1), zero calls unless opted in, BYOM verifier, env-only credentials, no new
   dependency, mocked tests only. Every row has a pinning test or an evidence file.
5. **Answer the questions the memo already resolved** (D1–D5) as "our position,
   override welcome" — config-vs-code, cost/latency, output treatment, advisory
   termination, opt-in UX. Expect D1 to be the discussion: upstream may prefer
   config-generalized group mapping (memo option b) over one named group in code.
6. **Disclose the env-merge finding** (`env-merge-design-note.md`) — it is a
   least-privilege observation about PEAK's MCP spawn path that an upstream
   maintainer would want to hear as a design note, not discover in review.
7. **Keep the fork-first proof artifacts** (this notes workspace, parallax #107–
   #110) as credibility: the integration already runs end-to-end on a second
   provider with tests and telemetry.

Also true and worth saying plainly: nothing in this arc requires upstream. The
fork delivers the full value to its users; engagement is optional and should stay
gated on that explicit decision.

## 4. What the fork ships today (end state)

- **parallax** (`2709859`): two backends (anthropic, openai_compat), keyless
  custom endpoints, a routing table that names its sources, self-describing cost telemetry — 538
  lib + 24 config_facts + 72 integration tests, all gates clean.
- **PEAK fork** (`3d063ef`): M4 opt-in verification wiring (one group, one
  agent, two tools) with T1–T6 mocked tests, README guidance, live validation;
  a research-notes workspace documenting every decision and every transcript.
- **Reproducibility**: the M2/M4 demos rerun from a clean checkout with only
  `mcp_servers.json` (+ local Ollama); strict-keyless variant makes zero
  external calls.

## 5. Open items (all optional, none blocking)

1. PEAK CLI `-a`/`-c` file-path quirk (divergence 3).
2. `inheritEnvironment` / null-key removal implementation (design recorded;
   first-PR scope in `env-merge-design-note.md` section 4).
3. Small-model sampling variance: tool usage in M2/M4 runs is not deterministic
   at 7B scale (final smoke pass: one M2 run skipped tools; one M4 attempt sent
   `"Medium"` — the rejection itself fixed by parallax PR #111). Final
   transcripts: `final-m2.log`, `final-m4-steered.log`,
   `final-m4-steered2.log`, `final-m4-unsteered.log`.
4. Carried-over hygiene: `is_capability_rejection` broad-token risk, rustls
   cap, live-smoke timeout.
5. Upstream engagement — explicitly gated on a human decision, per the memo.
