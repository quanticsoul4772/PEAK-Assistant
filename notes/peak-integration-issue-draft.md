**Memo:** Opt-In Heterogeneous Verification for the Hypothesis Phase — FINALIZED (M3)

> **Status: FINALIZED internal design memo — NOT to be filed at
> `Cisco-Talos/PEAK-Assistant`.** Policy: all work stays in our fork
> (`quanticsoul4772/PEAK-Assistant`); no issues or PRs on the upstream project.
> This memo is kept in issue shape so it could be filed later *only* on an
> explicit decision to engage upstream. The memo's design questions were
> resolved as internal design decisions D1-D5 on 2026-09-27 (see roadmap M3).

---

**Title:** Opt-in verification layer for hypothesis review via external MCP
server (heterogeneous model verification)

## Problem statement

PEAK's critics (`hypothesis-refiner-critic`, `summary_critic`,
`Discovery_Critic_Agent`, `hunt_plan_critic`) do freeform prose review. The
critic prompt in `hypothesis_refiner_cli.py` asks for "specific, actionable
feedback" against 8 criteria — but the review itself is produced by the same
class of model (often the *same* model instance) that produced the hypothesis.
Two consequences:

1. **Correlated self-critique.** When generator and critic share a model family,
   their failure modes correlate: fluent but wrong hypotheses get fluent but
   approving reviews. Agreement between the two is weak evidence.
2. **No checkable contract.** Prose review cannot be asserted against anything.
   A hypothesis that claims "base64 command lines appear in 468 process-creation
   events" is either checkable against the artifacts it cites or it isn't —
   today nobody checks.

## Proposal: an opt-in verification layer

Integrate [mcp-parallax](https://github.com/quanticsoul4772/mcp-parallax) (a
Rust MCP server of LLM correctives) as an **opt-in** verification stage in the
hypothesis-refinement loop:

- **`grounded_verify`** — claim-vs-artifact: each factual claim in a hypothesis,
  with locators to the research/ABLE artifacts it cites, is checked against
  those artifacts and returns a per-claim verdict. **Status: to be wired in M4**
  (D1/D2).
- **`verify`** — advisory ensemble passes: independent judgment of the claim
  with cross-pass agreement scoring. Advisory only: it informs the critic's
  feedback, it never vetoes. **Status: to be wired in M4** (D2/D4).
- Mapping: a new MCP server group (e.g. `hypothesis-verification`) whose tools
  are available to the **hypothesis critic** agent.

### Explicit non-goals / safety properties

- **Default behavior unchanged.** With no verification server configured, every
  phase behaves exactly as today (byte-identical prompts and outputs).
- **No mandatory extra model calls.** Verification runs only when the user has
  configured the group; the critic loop costs nothing extra otherwise.
- **BYOM preserved.** The verification server runs on its own model
  configuration (its own env), which the user controls; PEAK's
  `model_config.json` continues to govern PEAK agents untouched.
- **No credentials in tool arguments.** All server credentials live in the
  server's own environment (`mcpServers.*.env` supports `${ENV_VAR}`
  interpolation).

## Core argument: heterogeneous verification

The value is *independence*, not just "more checking":

> PEAK's agents reason with model A; parallax verifies with model B.
> Two passes over the same claim by two different model families do not share
> failure modes the way self-critique does. Agreement across heterogeneous
> models is meaningfully stronger evidence than agreement across two prompts to
> one model.

This is the same reason ensemble `verify` passes inside parallax are run
cross-pass — extended across the *system* boundary. A critic review that
survives both a same-model critic and a different-model verifier is
substantially more trustworthy than either alone.

**Caveat (stated in the docs too): consensus ≠ truth.** Two models
agreeing can still be jointly wrong — especially about niche security tooling,
where both may share training-data biases. The layer reports agreement
*structure* (which claims were independently supported/refuted, with what
confidence); it does not certify truth. Hunt-planning judgment stays with the
human.

## Why MCP (and why parallax)

- PEAK already consumes arbitrary user-provided MCP servers per phase
  (`serverGroups` in `mcp_servers.json`); the integration surface is one PEAK
  already standardized on.
- parallax's `grounded_verify`/`verify` return **structured verdicts**
  (schema-validated JSON: verdict, named findings, server-computed agreement
  confidence, completed-pass count — and from `check`, an auditable
  `formal_form`/`engine_result`/`witness`/`explanation`), which is exactly the
  "structured/checkable contract" gap identified above.
- parallax is separately maintained; nothing needs to be vendored into PEAK.

## Scope of the first contribution

1. **Zero-code demo (delivered):** parallax registered in an *existing*
   `mcp_servers.json` group works today — tools land in that phase's workbench.
   **Delivered 2026-09-27: evidence attached as `notes/m2-demo-evidence.md`**
   (+ verbatim `notes/m2-demo-transcript.log`), merged via fork PR #11.
2. **First PR (opt-in, minimal):** allow the hypothesis critic to receive tools
   from a configured `hypothesis-verification` group. One agent, two tools
   (`grounded_verify`, `verify`), mocked tests, **no default behavior change**.
   **This is M4, gated on this memo (M3) — see D1.**
3. Later (only if wanted upstream): ABLE-table `check` for quantitative claims,
   `checkpoint_*` turn review.

## Design questions and recorded decisions

All questions are now recorded design decisions (2026-09-27). Every decision
preserves the compatibility table at the bottom unchanged.
1. **D1 — Config vs code: option (a), one named group in code.** The first
   contribution (M4) extends the group→agent mapping for exactly one group
   (`hypothesis-verification`), exposed to one agent (the hypothesis critic).
   Generalizing the mapping into config (option b) is deferred until a second
   consumer exists; option (c) demo-only is already covered by M2.
2. **D2 — Opt-in extra model calls: acceptable.** They cost nothing unless the
   user configures the group, are never mandatory, and run on the verifier's
   own model configuration (BYOM). The M2 demo shows the mechanism works with
   a free local backend.
3. **D3 — Output treatment: critic guidance only.** Verification verdicts
   inform the critic's feedback; nothing is persisted into exported research
   documents in v1. Revisit after M4 field experience.
4. **D4 — Termination semantics: advisory forever (v1).** `grounded_verify`
   verdicts never influence the critic loop's termination condition; the loop
   keeps its existing termination rules. Unification is revisited only with a
   per-claim audit trail in place.
5. **D5 — Naming/UX: config presence is the opt-in.** No toggle, no per-phase
   setting: the group exists in `mcp_servers.json` or it does not. Documented
   in the README and the compatibility table.

## Compatibility summary

| Property | Guarantee |
|---|---|
| Default path | identical when the group is not configured |
| Extra calls | zero unless opted in |
| Model config | BYOM untouched; verifier model configured separately |
| Credentials | env-only, never tool arguments |
| New dependency | none (external MCP server, user-provided binary) |
| Tests | mocked unit/integration; no live calls in CI |
