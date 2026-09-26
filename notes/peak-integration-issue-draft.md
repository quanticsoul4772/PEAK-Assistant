# Draft PEAK Issue — Opt-In Heterogeneous Verification for the Hypothesis Phase

> **This is a draft for filing at `Cisco-Talos/PEAK-Assistant` (with a demo).**
> Not yet filed. Maintainer questions at the bottom must be answered (or
> explicitly offered as options) before/during filing.

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
  those artifacts and returns a per-claim verdict.
- **`verify`** — advisory ensemble passes: independent judgment of the claim
  with cross-pass agreement scoring. Advisory only: it informs the critic's
  feedback, it never vetoes.
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

**Caveat (we will say this in the docs too): consensus ≠ truth.** Two models
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

1. **Zero-code demo (exists now):** parallax registered in an *existing*
   `mcp_servers.json` group works today — tools land in that phase's workbench.
   We will attach a demo recording/output.
2. **First PR (opt-in, minimal):** allow the hypothesis critic to receive tools
   from a configured `hypothesis-verification` group. One agent, two tools
   (`grounded_verify`, `verify`), mocked tests, **no default behavior change**.
3. Later (only if wanted upstream): ABLE-table `check` for quantitative claims,
   `checkpoint_*` turn review.

## Maintainer questions

1. **Config vs code PR.** Today the group→agent mapping is a parameter default
   in code (`mcp_server_group_external: str = "research-external"` etc.), and
   the hypothesis agents have no MCP workbench at all. Should the first
   contribution:
   - (a) extend the mapping in code for one named group (small PR), or
   - (b) generalize group→agent mapping into `model_config.json`/another config
     key (bigger design, more flexible), or
   - (c) stay demo-only and not change PEAK code at all?
   Our reading is that (a) is smallest and (b) is where this naturally ends up.
2. **Are opt-in extra model calls acceptable in the hypothesis phase** at all
   (cost/latency), assuming they are off by default and never mandatory?
3. **Output treatment:** should verification verdicts be surfaced as critic
   guidance only (our proposal), or persisted into the exported research
   documents?
4. **Termination semantics:** should `grounded_verify` verdicts ever influence
   the critic loop's termination condition (e.g. unrefuted claims required to
   proceed), or remain advisory forever? We propose advisory-only for v1.
5. Any preferences on naming/UX for the opt-in (sidebar toggle? config presence
   alone? per-phase setting)?

## Compatibility summary

| Property | Guarantee |
|---|---|
| Default path | identical when the group is not configured |
| Extra calls | zero unless opted in |
| Model config | BYOM untouched; verifier model configured separately |
| Credentials | env-only, never tool arguments |
| New dependency | none (external MCP server, user-provided binary) |
| Tests | mocked unit/integration; no live calls in CI |
