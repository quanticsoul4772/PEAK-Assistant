# mcp-parallax BYOM Design — Provider-Agnostic Model Backend

**Status:** design proposal (not implemented). Verified against
`mcp-parallax@a539aacc` working tree, 2026-09-26.
See `peak-parallax-research-notes.md` §3.5–3.6 for the verified facts this builds on.

---

## 1. Problem

parallax's `ModelClient` seam is clean (a one-method async trait), but the only
production implementation is `AnthropicClient`, hard-wired to the Anthropic wire
format:

- `POST {base_url}/v1/messages` with `anthropic-version` header
  (src/client/anthropic.rs:237–239)
- structured output via `output_config.format = {type: "json_schema", schema}`
  (line 264); `effort` routed under `output_config` (261–272)
- `stop_reason` contract: `end_turn` ok, `max_tokens` → `AppError::Truncation`
  (billed), anything else → out-of-contract error (334–370)
- `ANTHROPIC_API_KEY` is required at startup (src/config.rs:176)

Any non-Anthropic model (OpenAI, Azure, local Ollama/vLLM, or PEAK's
`model_config.json` providers) is unusable except through an
Anthropic-compatible proxy. For the PEAK integration this matters twice: PEAK is
explicitly BYOM (azure/openai/anthropic/OpenAI-compatible), and the
*heterogeneous-verification* argument (Doc 3) needs the verifying model to be
independently chosen from the reasoning model.

**Where the coupling lives (complete inventory, verified):**
`src/client/anthropic.rs` (wire format, error taxonomy mapping), plus
`src/config.rs` (`ANTHROPIC_*` required/optional vars), plus
`src/routing.rs` (model *ids* are free strings — no coupling there). All
`complete()` call sites are already provider-neutral (they pass
`prompt` + `schema` and receive `Completion{value, input_tokens, output_tokens}`).

---

## 2. Options

### (a) Proxy via `ANTHROPIC_API_BASE` — zero code

Point `ANTHROPIC_API_BASE` at an Anthropic-compatible translation proxy
(LiteLLM, claude-code-router style, or a thin local shim) in front of any
provider.

- **Pros:** works today; no repo changes; per-call-site routing keeps working.
- **Cons:** external runtime dependency; JSON-schema fidelity depends on the
  proxy's translation; `stop_reason`/error taxonomy mapping is out of our
  control (proxy must emulate Anthropic semantics or parallax misclassifies
  truncations); token accounting stays proxy-reported; an extra network hop;
  one more process to secure.
- **Verdict:** good for a *demo* (roadmap M2), not a durable answer.

### (b) Native trait boundary + provider adapters — small code, durable

Implement `ModelClient` for additional wire formats behind new config. The trait
already exists (src/traits/client.rs:26) with `MockModelClient` (mockall) in
tests, so this is additive.

- **Pros:** no external process; correct error taxonomy locally; per-provider
  structured-output strategy chosen deliberately; token accounting native;
  aligns with PEAK's BYOM story.
- **Cons:** each adapter must faithfully translate structured output and finish
  reasons; more test surface; schema-dialect differences are real work.

### (c) (rejected) Wrap at the MCP layer / drop structured output

Degrading to "prompt asks for JSON" would break the validated-schemas contract
every tool depends on (`schema::validate` after each `complete`). Rejected.

**Recommendation:** (b) as the deliverable; (a) acceptable as a stopgap for M2
demos only, documented as such.

---

## 3. Proposed design (option b)

### 3.1 Keep the trait, add adapters

```
src/client/
  anthropic.rs      # existing AnthropicClient (unchanged behavior)
  openai_compat.rs  # NEW: OpenAI Chat Completions + /v1/models-agnostic
  mod.rs            # factory: build Box<dyn ModelClient> from config
```

- `OpenAiCompatClient` targets the Chat Completions shape used by OpenAI, Azure
  (via its OpenAI-compatible surface), Ollama, vLLM, LM Studio.
- `ModelClient::complete` signature is **unchanged**; no call-site edits
  required for correctness — call sites only change if we later want streaming.
- The factory keys off new config (§3.4). `ANTHROPIC_API_KEY` becomes
  conditionally required *only when the anthropic backend is selected*.

### 3.2 Structured-output translation

Per-adapter strategy, in preference order (fall back per model capability):

1. **JSON-schema mode:** `response_format: {type: "json_schema", json_schema: {...}}`
   (OpenAI structured outputs; Ollama/vLLM subset support).
2. **JSON-object mode:** `response_format: {type: "json_object"}` + the schema
   injected into the prompt; validate with the existing `schema::validate`.
3. **Tool-shim mode:** declare a single function whose parameters are the
   schema; force a tool call; parse `tool_calls[0].function.arguments`.
4. **Prompt-only (last resort):** schema in prompt; strict validation; failures
   surface as `AppError::ValidationFailure` — never silently accepted.

The sanitized schema parallax already computes (`mode.sanitized_schema`) is the
single source of truth for all four strategies.

### 3.3 Error-taxonomy translation (behavior parity core)

| parallax `AppError` | Anthropic signal | OpenAI-compat signal |
|---|---|---|
| `Truncation` (billed) | `stop_reason: "max_tokens"` | `finish_reason: "length"` |
| `Refusal` | refusal stop/content | `finish_reason: "content_filter"` / refusal field |
| out-of-contract `Client` | any other `stop_reason` | any other `finish_reason`, or empty `tool_calls`/`content` |
| `Timeout` | client timeout | client timeout |
| `RetriesExhausted` | retry policy exhaustion | same |

Token accounting: map `usage.{prompt,completion}_tokens` →
`Completion.{input_tokens, output_tokens}`; when a provider omits usage, return
zeros **and** emit a tracing warning (billing transparency is a parallax
invariant — see "the tokens were not free" comments in research/pipeline.rs).

### 3.4 Config additions (env, consistent with existing style)

```
PARALLAX_BACKEND=anthropic|openai_compat          # default: anthropic
OPENAI_API_KEY / OPENAI_API_BASE / OPENAI_MODEL    # openai_compat backend
PARALLAX_MODEL_<SITE|TIER>                         # unchanged, now names any backend's model
PARALLAX_EFFORT_<SITE|TIER>                        # unchanged; adapters that
                                                   # don't support effort ignore
                                                   # it with a startup notice
```

- Credentials stay in env only — **never in tool arguments** (guardrail).
- `ANTHROPIC_API_KEY` required iff `PARALLAX_BACKEND=anthropic`; symmetric for
  `OPENAI_API_KEY`. Startup validation mirrors today's strict
  `RoutingTable` validation (fail fast, name the offending variable).
- `effort` param on tools is already typed (`routing::Effort`); non-supporting
  adapters drop it at the wire and document the no-op.

### 3.5 What deliberately does NOT change

- Tool catalog, tool schemas, verdict semantics, the deterministic layer,
  ensemble pass logic, storage, memory, research pipeline.
- The 12-site routing table keeps its meaning; model *ids* simply may now name
  models on any backend (mixed backends across call sites: **allowed and useful**
  — e.g. VERIFY on a different provider than CHECK_TRANSLATE).

---

## 4. Call-site migration plan

1. **Land the seam:** factory + `OpenAiCompatClient` + config parsing. All 12
   routed sites automatically work through the factory (they receive
   `Arc<dyn ModelClient>` from `ClientPool::for_site`).
2. **Audit the 13th physical call:** `memory/consolidate.rs:239` (consolidation
   judge) borrows the Verify client — confirm it inherits the new backend with
   no special casing (expected: yes, verified wiring at server.rs:315).
3. **Wire-format parity tests per site** (§5) before declaring any site
   production-ready on the new backend.
4. **Effort handling:** sites that pass `effort` (verify, check, decide, …) get
   a documented no-op on adapters without effort support; `CHECK_TRANSLATE`'s
   violation-fed retry must be tested against JSON-mode fallbacks since retries
   depend on schema-violation error text.
5. **Token metering:** every site feeds `meter.add(model_for(site), in, out)`
   (e.g. pipeline.rs:685–703) — verify usage mapping so cost attribution stays
   correct.

Order of adapters: (1) OpenAI-compatible (covers OpenAI/Azure/Ollama/vLLM),
(2) native Azure AD quirks only if the compat surface proves insufficient.

---

## 5. Behavior-parity test plan

Existing infrastructure: `MockModelClient` (mockall) for unit tests;
`src/client/anthropic.rs` already has wire-mock tests asserting exact request
shapes (e.g. "unset effort must not appear on the wire", lines 495–521) — the
pattern to replicate.

Per call site (all 12 routed + consolidation), on **each** backend:

1. **Request-shape test:** captured wire request contains the schema in the
   chosen structured-output mode; effort present iff routed and supported.
2. **Happy-path parse:** canned response → `Completion` with correct value and
   token mapping.
3. **Taxonomy table test:** for each row of §3.3's table, the adapter maps the
   provider signal to the identical `AppError` variant the Anthropic client
   would produce (incl. `Truncation` carrying billed tokens).
4. **Schema-violation path:** malformed JSON / schema-invalid JSON →
   `ValidationFailure` identical to today's behavior (critical for
   `CHECK_TRANSLATE` retry semantics and research claim-drop semantics).
5. **Offline determinism:** all tests run without network (mock servers), so CI
   needs no keys; live smoke behind an opt-in marker (mirroring PEAK's
   `@pytest.mark.live` convention).

Minimum gate for "provider-agnostic": the full suite passes with
`PARALLAX_BACKEND=openai_compat` against a mock, plus one live smoke per tool
group (verify, check, research, memory) on a real OpenAI-compatible endpoint.

---

## 6. Risks

1. **Structured-output fidelity (highest):** local models' JSON-schema support
   is uneven; strict validation will reject more often → claim-drops in
   research, wasted passes in verify. Mitigation: strategy ladder §3.2, metrics
   on `ValidationFailure` rates per model, document supported tiers.
2. **Stop/finish-reason mapping:** providers use `length`/`content_filter`/
   `tool_calls` inconsistently; misclassification turns truncations into silent
   successes — the worst failure mode for a verifier. Mitigation: the §5.3
   taxonomy tests are the acceptance gate; default to `Client` error when
   unsure (fail loud).
3. **Streaming:** `ModelClient::complete` is unary — no streaming risk today.
   *Inferred:* nothing in the tool layer streams; PEAK integration doesn't
   need it. Keep it that way for v1.
4. **Token accounting:** providers omit or aggregate usage differently; wrong
   numbers silently corrupt the per-site cost records and `checkpoint` pricing
   (which "must name the routed review model… or a routed review is silently
   mispriced", server.rs:304–308). Mitigation: zeros + warning policy §3.3;
   pricing docs note unpriced backends.
5. **Effort semantics drift:** `output_config.effort` is Anthropic-specific;
   "same effort" on another backend is not the same computation. Document as
   best-effort, never as a guarantee.
6. **Scope creep:** model *routing* (which model per site) is orthogonal to
   backend; keep them orthogonal (already true in `routing.rs`).

---

## 7. Definition of done

- [ ] `PARALLAX_BACKEND=openai_compat` runs the full tool catalog against an
      OpenAI-compatible endpoint with zero call-site code changes beyond config.
- [ ] `ANTHROPIC_API_KEY` no longer required when a non-anthropic backend is
      selected; startup still fails fast on missing/invalid config.
- [ ] Taxonomy parity tests green for all `AppError` variants on both backends.
- [ ] All 13 physical call sites covered by per-site request-shape + happy-path
      tests (offline).
- [ ] Token accounting verified per site; mispricing warnings documented.
- [ ] README config section updated; no credentials in any example.
- [ ] `cargo test` green offline; live smoke opt-in only.
- [ ] Behavior with `PARALLAX_BACKEND=anthropic` byte-identical on the wire
      (existing wire-mock tests unchanged and passing).
