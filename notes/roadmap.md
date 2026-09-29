# Roadmap — PEAK × mcp-parallax

> **ARCHIVED 2026-09-27 — roadmap complete (M0–M4 ✅).** Final states:
> PEAK fork `main` (PRs #9–#40 merged; findings 1, 3, 9, 10 RESOLVED and
> implemented), parallax fork `main` at `62ef1bd` (PRs #107–#114).
> Divergence ledger: 10 findings — 0 open. Environment hardening 2026-09-29:
> null-key env removal (#39) + `inheritEnvironment` strict mode (#40),
> egress-verified live; planner grounding enforced end-to-end (#32–#35,
> hard-fail by default). 7B variance measured (`notes/7b-variance.md`):
> grounding held 20/20 runs across both models.
> Wrap-up: `project-wrapup.md`. Upstream engagement remains gated on an
> explicit human decision (see `peak-integration-issue-draft.md`).

Status legend: ✅ done · 🔧 in progress · ⬜ not started.
All milestones verified against real repo state as of 2026-09-27.

---

## M0 — Verification & workspace ✅

- ✅ Local paths resolved by discovery (no manual placeholders):
  - PEAK fork: `D:\Projects\PEAK-Assistant`
  - mcp-parallax: `C:\Development\Projects\MCP\project-root\mcp-servers\mcp-parallax`
  - mcp-reasoning: `C:\Development\Projects\MCP\project-root\mcp-servers\mcp-reasoning`
- ✅ Fork cloned (`origin` = quanticsoul4772/PEAK-Assistant, `upstream` = Cisco-Talos/PEAK-Assistant); `notes/research` branch created.
- ✅ Every carried-over claim confirmed or corrected (see research notes §8).
- ✅ SHAs/dates recorded: PEAK `dfabbb0` (2026-06-01), parallax `a539aacc` (2026-07-28, **dirty ×13**), mcp-reasoning `678d711` (2026-09-09).
- ✅ Deliverables in `notes/` committed on `notes/research`.
- ✅ (optional) `uv sync` + local PEAK run — done via the M2 demo (2026-09-27).

**M0 exit criteria:** all met.

## M1 — Provider-agnostic parallax + offline tests ✅

Per `parallax-byom-design.md`:

- ✅ `PARALLAX_BACKEND` config + factory in `src/client/mod.rs`.
- ✅ `OpenAiCompatClient` adapter with structured-output strategy ladder.
- ✅ Error-taxonomy parity tests (Truncation/Refusal/Client mapping) per backend.
- ✅ Per-call-site request-shape + happy-path tests for all 12 physical call
  sites (covering 13 LLM-backed operations: 12 routed + memory consolidation
  borrowing Verify's client).
- ✅ Token-accounting mapping verified; zero-usage warning policy.
- ✅ `cargo test` green fully offline; live smoke opt-in.
- ✅ README/config docs updated.

**Exit criteria:** full tool catalog runs against an OpenAI-compatible endpoint
with only config changes; anthropic backend wire-identical. All met — delivered
as quanticsoul4772/mcp-parallax PR #107 (merged `eadda0c`, 2026-09-27).
Live-endpoint validation landed with the M2 Ollama run — see `notes/m2-demo-evidence.md`.

## M2 — Zero-PEAK-code demo ✅

- ✅ Register parallax in a local `mcp_servers.json` **existing** group (this is
  the only wiring that is config-only — group→agent mapping is code).
- ✅ Run one PEAK phase end-to-end with parallax tools available in the
  workbench; capture transcript/output as demo evidence.
- ✅ Document the exact `mcpServers`/`serverGroups` snippet (env-interpolated,
  no secrets committed) and which tools the agent actually invoked.

**Exit criteria:** reproducible demo on a clean PEAK checkout with only
`mcp_servers.json` + env added.
Met 2026-09-27 — wiring, transcript excerpts and divergence list in
`notes/m2-demo-evidence.md`. Prerequisites are environment-only (built parallax
binary at `e7f12f8`; Ollama with `qwen2.5:7b`; a model entry with
`function_calling` flags). No PEAK source file changed.

## M3 — Finalize the integration proposal (fork-only) ✅

**Policy: all work stays in our fork. No issues or PRs on
`Cisco-Talos/PEAK-Assistant`.**

- ✅ Finalize `peak-integration-issue-draft.md` as an internal design memo
  (attach demo links/results from M2). Keep it in issue shape so it could be
  filed upstream *only if* we ever explicitly decide to engage. **Done
  2026-09-27: memo finalized, M2 evidence attached (`notes/m2-demo-evidence.md`).**
- ✅ Resolve the maintainer questions as internal design decisions (config vs
  code, opt-in call policy, output treatment). **Recorded as D1–D5 in the
  memo, 2026-09-27.**
- ⬜ Optionally watch upstream's issues/PRs read-only for context; never post.

**Exit criteria:** memo finalized and decisions recorded in the fork.
Met 2026-09-27 (decisions D1–D5).

## M4 — First small integration PR in our fork (optional) ✅

A PR against **our fork's `main` only** — never upstream. Strictly minimal,
opt-in only:

- ✅ One agent (hypothesis critic) can receive tools from one configured group
  (`hypothesis-verification`).
- ✅ Two tools surfaced: `grounded_verify` (claim-vs-artifact), `verify`
  (advisory). — allowlist enforced by `_AllowlistWorkbench`
- ✅ Mocked tests only; no live calls in CI. — T1–T6 in
  `tests/unit_tests/test_hypothesis_verification_wiring.py`
- ✅ **No default behavior change** — identical prompts/outputs when the group
  is absent. — pinned by T1 construction-parity test
- ✅ PR description states guarantees from the memo's compatibility table.

**Exit criteria:** PR merged into our fork's `main`; demo (M2) remains the
fallback value story.
Met 2026-09-27 — fork PR #14 merged (`8297c13`, commit `be294c3`):
opt-in `hypothesis-verification` group → critic via `--verification-group`,
allowlist {grounded_verify, verify}, never-raising resolver, ruff/mypy clean,
222 passed + 1 skipped (`-m "not live"`).
Live end-to-end validation 2026-09-27: `notes/m4-live-validation.md` — the
steered critic called `verify` and received a `refuted` ensemble verdict from
qwen2.5:7b; D3 guidance-only held; unsteered run confirms the default path
stays silent unless opted in.

---

## First-week checklist

Day 1–2
- [x] Discover repos, verify claims, record provenance (M0)
- [x] `uv sync` in the PEAK fork; run `make checks` baseline
- [x] Confirm `cargo test` baseline in a scratch copy of parallax (do NOT build
      in the read-only checkout; copy or work in a fork/branch of your own —
      Z3 needs cmake + MSVC Build Tools)

Day 3–4
- [x] Start M1: factory + `OpenAiCompatClient` skeleton with mock tests
- [x] Write the taxonomy-parity test harness first (it defines "done")

Day 5
- [x] M2 demo prep: draft the `mcp_servers.json` snippet with a local
      OpenAI-compatible model (e.g. Ollama) as parallax's backend
- [x] Rehearse the demo end-to-end; note every place behavior diverges from
      Anthropic-backend behavior (feeds M1 bug list)

Ongoing hygiene
- [ ] **Never touch `Cisco-Talos/PEAK-Assistant`** — no pushes, PRs, or issues.
      All PEAK-side work lives in our fork (`quanticsoul4772/PEAK-Assistant`).
      Reading/fetching upstream for updates is fine.
- [ ] Never commit `.env`, certs, `model_config.json`/`mcp_servers.json` edits
- [ ] Keep both MCP checkouts read-only (they are the user's working trees;
      parallax's is currently dirty on `053-diverge-pass-count` — leave it so)
- [ ] PEAK work happens only on `notes/research` or `feat/*` cut from our
      fork's `main` (optionally synced from `upstream/main`); never commit
      directly to `main`
