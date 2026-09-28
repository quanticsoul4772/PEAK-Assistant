# M4 live validation — opt-in verification path end-to-end

Date: 2026-09-27, after fork PR #14 merged (`8297c13`). PEAK fork `main` at
`5bdb0a1`; parallax `main` at `e7f12f8` (PR #109 landed later, see note 6). Backend:
Ollama 0.34.0 with `qwen2.5:7b`, keyless `openai_compat`. Both full transcripts are
committed verbatim: `m4-live-transcript-unsteered.log` (95 lines) and
`m4-live-transcript-steered.log` (113 lines); quotes below are verbatim.

## 1. Configuration delta (from the M2 demo state)

One addition to the gitignored `mcp_servers.json`: a second group on the same
parallax server entry. No other change — no code, no `model_config.json` edit.

```json
"serverGroups": {
    "data_discovery": [
      "parallax"
    ],
    "hypothesis-verification": [
      "parallax"
    ]
  }
```

Pre-run validation: `uv run mcp-status -v` -> "2 servers ready", "All MCP servers
are properly configured!". CLI wiring: `--verification-group hypothesis-verification`.

## 2. Run 1 — unsteered: wiring proven, tool not called

Command: `uv run python -m peak_assistant.hypothesis_assistant.hypothesis_refiner_cli
-y <hypothesis> -r <research.md> --no-feedback --verification-group hypothesis-verification -v`
-> exit 0. Transcript: `m4-live-transcript-unsteered.log`.

The opt-in path engaged exactly as designed:

```
Verification tools enabled for the hypothesis critic via server 'parallax'.
```

parallax booted with `backend="openai_compat" model=qwen2.5:7b` (routing table logged,
12 call sites), the critic completed its 8-criteria review, and the loop terminated on
`YYY-HYPOTHESIS-ACCEPTED-YYY`. **But the critic never called a verification tool** — no
`ToolCallRequestEvent` appears in the transcript. A 7B model reviewing a vague one-line
hypothesis chose to answer from its own judgment. Wiring proven; tool path unexercised.

## 3. Run 2 — steered: real tool call, real refuted verdict

Same command plus a context file (`-c`) instructing the critic to ground its
ASSERTION QUALITY score in the verification tools. Exit 0. Transcript:
`m4-live-transcript-steered.log`.

The critic called `verify` (the advisory ensemble) on the hypothesis:

```
---------- ToolCallRequestEvent (critic) ----------
[FunctionCall(id='call_bvh6bzfj', arguments='{"claim":"The attacker used PowerShell for lateral movement inside the victim network."}', name='verify')]

---------- ToolCallExecutionEvent (critic) ----------
[FunctionExecutionResult(content='{"confidence":0.6666666666666666,"findings":["The claim does not specify the attacker\'s method of lateral movement, only that PowerShell was used. This does not conclusively prove PowerShell was the method of lateral movement.","A single concrete counterexample to this claim would be if the attacker used a different tool or method (e.g., WMI, PsExec) for lateral movement."],"passes":3,"verdict":"refuted"}', name='verify', call_id='call_bvh6bzfj', is_error=False)]
```

The verdict is parallax's three-pass ensemble judgment, computed locally by
qwen2.5:7b — **`verdict: "refuted"` at confidence 0.67**, with the ensemble's
reasoning in `findings`: the claim does not establish PowerShell as *the* method
of lateral movement, and a counterexample method (WMI, PsExec) would refute it.

parallax-side telemetry for the invocation (3 passes, local, keyless):

```
2026-09-27T19:21:08.918648Z  INFO serve_inner: mcp_parallax::telemetry: invocation recorded invocation.id=229f50fb-2bad-4540-8c2f-1511c3c34b5b session.id=c1c78d82-296d-48ec-8e07-bb646d200691 gen_ai.operation.name=verify gen_ai.request.model=qwen2.5:7b gen_ai.usage.input_tokens=745 gen_ai.usage.output_tokens=223 gen_ai.response.finish_reasons=success cost.usd=0.009300000000000001 latency.ms=5835
```

D3 (guidance-only) held: the verdict flowed into the critic's review text — its
ASSERTION QUALITY feedback ends with "Clarify that PowerShell was used as part of
lateral movement, not the only method", directly echoing the ensemble's first
finding — and the loop still terminated on its own `YYY-HYPOTHESIS-ACCEPTED-YYY`
condition. Nothing was persisted into exports; no termination behavior changed.

## 4. Findings

1. **RESOLVED 2026-09-27 — steering is required for small models.** The unsteered
   7B critic reviewed normally and never reached for the tools; with one
   context-file instruction it called `verify` immediately. This is model
   capability, not wiring — README/memo should note that opt-in verification
   benefits from prompting the critic to use it. Follow-on: the final smoke pass
   also caught the 7B model sending `"effort":"Medium"` (capitalized), which the
   then-derived serde impl rejected; fixed by parallax PR #111 (tool-argument
   deserialization now shares `Effort::parse` with the env-var path), verified
   live — `"Medium"` returns a verdict with `cost.estimated=true`.
2. **Tool choice matched the tool contracts.** Given a bare hypothesis with no
   artifact locators, the critic picked `verify` (advisory, claim-only) over
   `grounded_verify` (claim-vs-artifact) — exactly the division of labor the memo
   describes.
3. **Heterogeneous verification behaved as argued.** The ensemble pushed back on
   an overclaiming hypothesis (`refuted`, 0.67) and the critic's feedback echoed
   the ensemble finding while termination stayed untouched — consensus structure
   informing judgment, never certifying truth (memo caveat intact).
4. **RESOLVED 2026-09-27** — Keyless and local throughout: all three ensemble
   passes ran on `qwen2.5:7b` via `http://localhost:11434/v1` with no API key. The
   telemetry `cost.usd=0.0093` was parallax's notional price-table accounting, not
   spend. Investigated and decided against zeroing for localhost (cost is
   observability-only, and the endpoint — not the backend — decides "free");
   the fix landed instead as parallax PR #110: the invocation log line
   now carries `cost.estimated` (`true` = Opus-tier fallback over-estimate for
   an unknown model id, `false` = catalog price), verified live on Ollama:
   `cost.usd=0.00684 cost.estimated=true`. See
   `notes/parallax-telemetry-fixes.md` for the full decision record.
5. **Default path untouched, per test T1.** The negative control is the merged
   test suite: T1 pins that `refiner()` with no `mcp_server_group` never attempts
   MCP and constructs the critic without a workbench.
6. **parallax version note.** Both runs predate parallax PR #109: the routing
   lines still read `source=ANTHROPIC_MODEL` (divergence 2, since fixed and
   verified live with the #109 binary). The label is cosmetic and does not
   affect this validation's conclusions; no re-run required.
