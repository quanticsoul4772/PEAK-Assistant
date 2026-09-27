# notes/ — PEAK x mcp-parallax research workspace

Research and design documents for integrating `mcp-parallax` (a Rust MCP server of
LLM "correctives") into PEAK-Assistant as an opt-in verification layer. These are
planning artifacts only — no code changes to PEAK are proposed here yet.

**Scope note:** everything in these docs was verified against the local source
checkouts listed below on 2026-09-26. Carried-over claims that did not survive
verification are marked **Correction** in `peak-parallax-research-notes.md`.
Claims that could not be confirmed are marked **TODO** (none currently).
`mcp-reasoning` is explicitly out of scope for design; it appears for context only.

## Resolved local paths (discovered, not assumed)

| Repo | Local path | Role |
|------|-----------|------|
| PEAK-Assistant (fork) | `D:\Projects\PEAK-Assistant` | this repo; docs land in `notes/` |
| mcp-parallax | `C:\Development\Projects\MCP\project-root\mcp-servers\mcp-parallax` | READ-ONLY research input |
| mcp-reasoning | `C:\Development\Projects\MCP\project-root\mcp-servers\mcp-reasoning` | READ-ONLY research input (out of scope) |

Discovery note: two red-herring paths exist on this machine and are **not** the
checkouts — `C:\Users\rbsmi\.config\manicode\projects\mcp-parallax` (chat
metadata only) and `D:\Projects\rawcell-agent\mcp-reasoning` (empty directory;
an uninitialized gitlink inside the rawcell-agent repo). The real checkouts were
located via agent-tool cache paths pointing at
`C:\Development\Projects\MCP\project-root\mcp-servers\`.

## Provenance (captured 2026-09-26T11:59:34-07:00)

| Repo | HEAD | Commit date | Branch checked out | Tree state |
|------|------|-------------|--------------------|------------|
| PEAK-Assistant (D:\Projects\PEAK-Assistant) | `dfabbb0fbcc27292ecbb8e32beeccda372bc0783` | 2026-06-01 | `notes/research` (cut from `upstream/main`) | clean |
| mcp-parallax | `a539aacc49ae6e0b5f21fd33a2cda856c223da29` | 2026-07-28 | `053-diverge-pass-count` (NOT main) | **dirty — 13 modified files** |
| mcp-reasoning | `678d7112a3cc30c846fc51ace64c3ca3e97d5186` | 2026-09-09 | `fix/retired-sonnet4-default` (NOT main) | clean |

Remotes: PEAK fork `origin` = `https://github.com/quanticsoul4772/PEAK-Assistant.git`,
`upstream` = `https://github.com/Cisco-Talos/PEAK-Assistant.git`.
mcp-parallax and mcp-reasoning origins are `quanticsoul4772/mcp-parallax` and
`quanticsoul4772/mcp-reasoning` respectively.

**Dirty state of mcp-parallax (read as-is, per handoff rules — nothing stashed,
reset, or modified):** `CHANGELOG.md`, `CLAUDE.md`, `README.md`,
`examples/common/mod.rs`, `specs/012-diverge-perspectives/contracts/diverge.md`,
`specs/012-diverge-perspectives/research.md`, `specs/012-diverge-perspectives/spec.md`,
`src/config.rs`, `src/main.rs`, `src/modes/diverge.rs`, `src/modes/mod.rs`,
`src/server.rs`, `tests/integration.rs`. All findings below describe the working
tree as read on 2026-09-26, which may differ from commit `a539aacc`.

Both MCP checkouts were left untouched (no fetch, no edits). Their SHAs refer to
local state; local branches may be behind their remotes.

## Documents

1. `peak-parallax-research-notes.md` — verified research findings, phase mapping,
   corrections to the carried-over brief.
2. `parallax-byom-design.md` — design for making mcp-parallax provider-agnostic
   (BYOM), with migration and test plans.
3. `peak-integration-issue-draft.md` — **finalized** internal design memo
   (M3, 2026-09-27): opt-in heterogeneous verification layer; design
   questions resolved as recorded decisions D1–D5; M2 evidence attached.
4. `roadmap.md` — M0–M4 milestones and first-week checklist.
5. `m2-demo-evidence.md` — M2 zero-PEAK-code demo evidence: verbatim config
   snippets, transcript excerpts, divergence list, exit-criteria mapping
   (2026-09-27; feeds M3 memo attachment).
6. `m2-demo-transcript.log` — verbatim transcript of the M2 demo run
   (111 lines; committed for provenance).
7. `m4-implementation-plan.md` — M4 pre-implementation plan (survey of
   hypothesis-critic call sites, D1 wiring design, mocked-test plan T1–T6,
   risks). Roadmap M4 items tick only when the feat PR lands.
8. `m4-live-validation.md` — live end-to-end validation of the M4 opt-in
   path (2026-09-27): steered critic calls `verify`, gets a refuted ensemble
   verdict from qwen2.5:7b, honors guidance-only (D3). Unsteered run shows
   wiring engages without forcing tool use.
9. `m4-live-transcript-unsteered.log` / `m4-live-transcript-steered.log` —
   verbatim transcripts of both validation runs (committed for provenance).
10. `parallax-telemetry-fixes.md` — decision record for the two parallax
    follow-ups found during the demos: routing source label (PR #109) and
    `cost.estimated` on the log line (PR #110), with live verifications and
    the do-not-zero cost-accounting rationale.
11. `m2-keyless-rerun-transcript.log` — verbatim transcript of the
    strict-keyless M2 rerun (empty-string env scrub, zero external calls).

## Branch strategy (this repo)

- `main` — mirrors `upstream/main`; never commit work here.
- `notes/research` — this branch; long-lived home for these docs.
- `feat/<name>` — short-lived PR branches cut from fresh `main`.

## Upstream policy

**All work stays in our fork (`quanticsoul4772/PEAK-Assistant`). Nothing is
posted to `Cisco-Talos/PEAK-Assistant`** — no PRs, no issues, no pushes.
Reading/fetching upstream for updates is fine. `peak-integration-issue-draft.md`
is therefore an internal design memo, not a pending filing (roadmap M3).
(Historical note: upstream PR #95 was opened by mistake and closed the same
day; GitHub retains closed PRs, so it remains visible in upstream's history.)

Do not commit `.env`, `model_config.json`/`mcp_servers.json` edits, TLS certs, or
anything from the MCP server checkouts into this fork.
