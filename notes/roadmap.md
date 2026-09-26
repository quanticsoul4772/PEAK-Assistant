# Roadmap — PEAK × mcp-parallax

Status legend: ✅ done · 🔧 in progress · ⬜ not started.
All milestones verified against real repo state as of 2026-09-26.

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
- ⬜ (optional) `uv sync` + local PEAK run to have a working demo environment.

**M0 exit criteria:** all met.

## M1 — Provider-agnostic parallax + offline tests ⬜

Per `parallax-byom-design.md`:

- ⬜ `PARALLAX_BACKEND` config + factory in `src/client/mod.rs`.
- ⬜ `OpenAiCompatClient` adapter with structured-output strategy ladder.
- ⬜ Error-taxonomy parity tests (Truncation/Refusal/Client mapping) per backend.
- ⬜ Per-call-site request-shape + happy-path tests for all 12 physical call
  sites (covering 13 LLM-backed operations: 12 routed + memory consolidation
  borrowing Verify's client).
- ⬜ Token-accounting mapping verified; zero-usage warning policy.
- ⬜ `cargo test` green fully offline; live smoke opt-in.
- ⬜ README/config docs updated.

**Exit criteria:** full tool catalog runs against an OpenAI-compatible endpoint
with only config changes; anthropic backend wire-identical.

## M2 — Zero-PEAK-code demo ⬜

- ⬜ Register parallax in a local `mcp_servers.json` **existing** group (this is
  the only wiring that is config-only — group→agent mapping is code).
- ⬜ Run one PEAK phase end-to-end with parallax tools available in the
  workbench; capture transcript/output as demo evidence.
- ⬜ Document the exact `mcpServers`/`serverGroups` snippet (env-interpolated,
  no secrets committed) and which tools the agent actually invoked.

**Exit criteria:** reproducible demo on a clean PEAK checkout with only
`mcp_servers.json` + env added.

## M3 — Open the PEAK issue ⬜

- ⬜ File `peak-integration-issue-draft.md` (finalized with demo links/results)
  at Cisco-Talos/PEAK-Assistant.
- ⬜ Include the heterogeneous-verification argument and the "consensus ≠ truth"
  caveat; answer maintainer questions with concrete options.
- ⬜ Track responses; adjust M4 scope to maintainer preference (config-only →
  code PR question is the decisive one).

**Exit criteria:** issue filed, maintainer direction on Q1/Q2 known.

## M4 — First small PEAK PR (optional, gated on M3) ⬜

Strictly minimal, opt-in only:

- ⬜ One agent (hypothesis critic) can receive tools from one configured group
  (`hypothesis-verification`).
- ⬜ Two tools surfaced: `grounded_verify` (claim-vs-artifact), `verify`
  (advisory).
- ⬜ Mocked tests only; no live calls in CI.
- ⬜ **No default behavior change** — identical prompts/outputs when the group
  is absent.
- ⬜ PR description states guarantees from the issue's compatibility table.

**Exit criteria:** PR merged or explicitly declined; either way the demo (M2)
remains the fallback value story.

---

## First-week checklist

Day 1–2
- [x] Discover repos, verify claims, record provenance (M0)
- [ ] `uv sync` in the PEAK fork; run `make checks` baseline
- [ ] Confirm `cargo test` baseline in a scratch copy of parallax (do NOT build
      in the read-only checkout; copy or work in a fork/branch of your own —
      Z3 needs cmake + MSVC Build Tools)

Day 3–4
- [ ] Start M1: factory + `OpenAiCompatClient` skeleton with mock tests
- [ ] Write the taxonomy-parity test harness first (it defines "done")

Day 5
- [ ] M2 demo prep: draft the `mcp_servers.json` snippet with a local
      OpenAI-compatible model (e.g. Ollama) as parallax's backend
- [ ] Rehearse the demo end-to-end; note every place behavior diverges from
      Anthropic-backend behavior (feeds M1 bug list)

Ongoing hygiene
- [ ] Never commit `.env`, certs, `model_config.json`/`mcp_servers.json` edits
- [ ] Keep both MCP checkouts read-only (they are the user's working trees;
      parallax's is currently dirty on `053-diverge-pass-count` — leave it so)
- [ ] PEAK work happens only on `notes/research` or `feat/*` cut from fresh
      `upstream/main`; never commit to `main`
