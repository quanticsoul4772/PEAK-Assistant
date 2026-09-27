# Parallax telemetry fixes — decision record (#109, #110)

Date: 2026-09-27. Both items were found during the PEAK M2/M4 demo runs, fixed in
the parallax fork, merged with all 8 CI checks green, and verified live against
Ollama (`qwen2.5:7b`, keyless `openai_compat`). This file records what changed and
the one design decision made along the way (cost accounting).

## 1. Routing source label — parallax PR #109 (merged `5df9656`)

**Found:** on `PARALLAX_BACKEND=openai_compat`, every fall-through call site logged
`source=ANTHROPIC_MODEL` although the model resolved from `OPENAI_MODEL`. The
routing table exists so an operator can tell a deliberate route from a fall-through
(018 FR-005); naming a variable that did not supply the model defeats that.

**Fix:** new `DefaultVar` enum (`AnthropicModel | OpenAiModel`); `RouteSource::Default`
carries the backend default that actually supplied the model, selected by config at
resolution time and threaded through `RoutingTable::from_env`/`resolve`/`single`.
Anthropic-backend output unchanged (all fixtures pass `DefaultVar::AnthropicModel`).
New test: `the_default_route_names_the_backend_default_variable`.

**Live verification (post-merge, binary rebuilt):**

```
INFO mcp_parallax::server: routing resolved call_site="verify" tier="judgment" model=qwen2.5:7b source=OPENAI_MODEL
```

## 2. `cost.estimated` on the invocation log line — parallax PR #110 (merged `2709859`)

**Found:** demo transcripts showed `cost.usd=0.0093` for a free local model with no
hint the figure was notional.

**Investigation (read-only on main):** `cost_usd()` prices from a static catalog
(`PRICING_PER_MTOK`, cached from public pricing pages, invoice-exactness explicitly
not required by spec); unknown model ids fall back to **Opus-tier rates**
(5.00/25.00 per MTok) as a conservative over-estimate. Reproduced all three observed
demo figures exactly with that formula. `pricing_known(model)` already distinguishes
catalog price from fallback, SQLite stores the flag per model row (018 D4), and OTel
exports `parallax.cost_estimated` — the console line was the one surface missing it.
Cost is observability-only: no budget, limit, or gate consumes it anywhere.

**Decision — do NOT zero `cost.usd` for local endpoints.** Reasons: (a) the
`openai_compat` backend does not imply free — the *endpoint* does, and the same
model id can sit behind a paid hosted gateway, which a model-id-only function cannot
see; (b) zeroing conflates "costs nothing" with "cost unknown", discarding the
existing honest signal; (c) tokens and latency are the real resource story on local
backends and are already recorded.

**Fix (chosen instead):** `cost.estimated` on the invocation log line — `false`
means catalog-priced, `true` means Opus-tier fallback over-estimate. The name
mirrors the existing surfaces rather than inventing a synonym (SQLite stores
`pricing_known` per model row; OTel exports `parallax.cost_estimated`). New test
`the_invocation_log_line_reports_whether_the_cost_is_estimated` captures the emitted
line through a buffered `MakeWriter` and pins both values.

**Live verification (post-merge, binary rebuilt from `2709859`):**

```
INFO serve_inner: mcp_parallax::telemetry: invocation recorded invocation.id=b52bafef-9d8d-480b-b88d-a3dd9832f3cb session.id=f1fe01d8-d65d-4a4a-b09a-74312e09ef5e gen_ai.operation.name=verify gen_ai.request.model=qwen2.5:7b gen_ai.usage.input_tokens=733 gen_ai.usage.output_tokens=127 gen_ai.response.finish_reasons=success cost.usd=0.006840000000000001 cost.estimated=true latency.ms=9379
```

A cancel-path probe (stdin closed mid-invocation) also showed the correct edge
semantics: `finish_reasons=cancelled`, 0 tokens, `cost.estimated=false` — an empty
usage set prices from nothing, so it is neither estimated nor measured.

## 3. Strict-keyless rerun — divergence 1 closed (config-only)

PEAK's env merge (`mcp_config.py`: `os.environ.copy()` then `update(config.env)`)
can override but not delete, and parallax normalizes blank keys to absent
(`.filter(|key| !key.trim().is_empty())`). Setting each leaked key to the empty
string in the `env` block therefore neutralizes the parent-environment leak with
zero code changes:

```json
"env": {
  "PARALLAX_BACKEND": "openai_compat",
  "OPENAI_API_BASE": "http://localhost:11434/v1",
  "OPENAI_MODEL": "qwen2.5:7b",
  "DATABASE_PATH": "...",
  "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": "", "VOYAGE_API_KEY": "", "BRAVE_API_KEY": ""
}
```

Rerun (`notes/m2-keyless-rerun-transcript.log`, exit 0): zero voyage/brave/
anthropic/openai.com markers; no `surface` call; the one tool invocation (`verify`)
attributes to `qwen2.5:7b` (`cost.usd=0.00754`, which under the post-#110 binary
would also carry `cost.estimated=true`). The M2 exit criterion now holds in its
strict form: clean checkout + `mcp_servers.json` + local Ollama, zero external egress.

## 4. Status ledger

| Item | Status |
|---|---|
| Divergence 1 — env-merge key leak | RESOLVED (empty-string scrub; rerun verified) |
| Divergence 2 — routing source label | RESOLVED (parallax PR #109; live-verified) |
| Divergence 3 — PEAK CLI `-a`/`-c` file-path quirk | documented (upstream-shaped, low priority) |
| Divergence 4 — 7B model holds the loop | positive finding (see M2/M4 evidence) |
| cost.usd on localhost | RESOLVED as documentation + `cost.estimated` (PR #110); zeroing declined |
