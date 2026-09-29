# 7B sampling-variance experiment: tool usage in data_discovery

Date: 2026-09-29. Fork-only evidence run. Companion to open item 3 in
`project-wrapup.md` ("small-model sampling variance").

## Setup

- PEAK data_discovery agent (`uv run python -m peak_assistant.data_assistant`),
  `--no-feedback`, verbose, against the live Splunk trial container
  (`winrm_hunt`, sourcetype `winrm:demo`) via `splunk-mcp`, with parallax in
  the same group (strict env mode, null-removed keys).
- Fixed prompt set across all runs: identical `-y` hypothesis, `-r` research,
  `-a` ABLE, `-c` local-context files. Ollama at temperature defaults.
- 10 runs per discovery model: `qwen2.5:7b` (the fork default) and
  `llama3.1:8b` (via `model_config.json` `defaults.model` switch; the
  parallax memory backend stayed on its own configured model).
- Raw transcripts: `/tmp/peak-variance/{qwen,llama}-{1..10}.log` (session-local).

## Results

| Metric | qwen2.5:7b | llama3.1:8b |
|---|---|---|
| Exit 0 | 10/10 | 10/10 |
| Clean `YYY-TERMINATE-YYY` | 10/10 | 10/10 |
| Any MCP tool call | 9/10 | 10/10 |
| `get_indexes` | 9/10 | 7/10 |
| `search_oneshot` (real SPL executed) | 1/10 | 6/10 |
| `UNVERIFIED` warning | 0/10 | 0/10 |
| Fabricated index names (excl. context echo) | 0/10 | 0/10 |
| Duration range | 13–22 s | 25–132 s |

Variance *within* each model, same prompt:

- qwen skipped tools entirely in 1/10 runs (run 4: answered from the prompt
  context alone; correct index, plausible-but-unverified field list).
- qwen called `search_oneshot` (actually executed SPL) in only 1/10 runs;
  the other 9 stopped after `get_indexes`.
- llama never skipped tools, and executed real SPL in 6/10 runs — but its
  durations swing 5× (25–132 s), including multi-minute reasoning stalls.

## Conclusions

1. **The finding-9/10 enforcement chain held everywhere.** 20/20 runs cite
   only `winrm_hunt`; zero fabricated index names; `UNVERIFIED` stayed silent
   (search-capable group present). Tool-skipping no longer produces
   ungrounded inventory — the report either reflects a real round-trip or is
   visibly derived from what the agent saw.
2. **Tool usage at 7B is genuinely stochastic**, confirming open item 3:
   same model, same prompt → tool/no-tool and tool-depth differ run to run.
   qwen: 90% tool rate but shallow (get_indexes only in 8 of those 9);
   llama: 100% tool rate and 60% deep (real SPL). If discovery *depth*
   matters, llama3.1:8b is the stronger discovery backend on this stack;
   qwen stays the default for planning (see the plan-grounding evidence in
   `project-wrapup.md` §2 row 10).
3. **The #38 fix (empty agent entries layering over defaults) mattered**:
   switching `defaults.model` is the only change needed to move discovery to
   llama — with the pre-fix shadowing behavior, unrelated `"agents"` stubs
   broke startup entirely.
4. **Config note**: running llama through PEAK requires a `model_info` block
   for `llama3.1:8b` in `providers.ollama-local.models` (autogen rejects the
   name without it). Added locally; worth adding to
   `mcp_servers.json.example`-style documentation if llama becomes a
   documented alternative.

## Head-to-head: planning on qwen vs llama discovery reports

Date: 2026-09-29. One discovery report generated per model (both exit 0,
both grounded), then 5 planning runs per report (10 plans, qwen2.5:7b
planner for both arms, identical prompts). Metrics computed with the
deterministic rules from `plan_grounding.py` (fenced-`spl` extraction,
FROM_UNIXTIME ban, tstats-after-pipe check).

| Metric | Plans on qwen report | Plans on llama report |
|---|---|---|
| Exit 0 | 5/5 | 5/5 |
| GROUNDING WARNING/ERROR | 0/5 | 0/5 |
| Indices cited | winrm_hunt only, 5/5 | winrm_hunt only, 5/5 |
| SPL queries extracted | 78 | 100 |
| Pass deterministic validity | **65/78 (83%)** | **73/100 (73%)** |
| `tstats` after a pipe (invalid) | 13 | 27 |
| Fence-case typos (```` ```sPL ````) | 0 | 24 (one whole run used `sPL`) |
| Fields used match discovery report | yes (ProcessCommandLine/ProcessCreatorUser/ProcessParentProcessId dominate) | partially — mostly `raw=` wildcard searches, not the structured fields llama's own report claimed existed |

Reading:

- **Grounding is a solved layer**: 10/10 plans fully grounded regardless of
  which model produced the discovery report — the #32–#35 chain is
  model-independent at the plan stage.
- **Query quality tracks the discovery report's specificity.** The qwen
  report named concrete CIM-style fields (ProcessCommandLine, …), and plans
  built on it emitted 83% deterministic-valid queries referencing those
  fields. The llama report named only generic fields (host, user, raw),
  and its plans leaned on `raw=*powershell.exe*` wildcard scans — valid
  SPL less often (73%), and structurally weaker (full-scan wildcards vs
  field filters). Garbage-in echoes: a vague discovery report degrades the
  plan even when the planner is identical.
- **New failure shape found**: llama wrote 24 fenced blocks as ```` ```sPL ````
  — a fence typo that would defeat any extraction expecting lowercase
  `spl` (plan_grounding is case-insensitive on the content checks, but a
  strict extractor is not). Worth a tolerant-extraction fix in
  `plan_grounding.py::extract_spl_queries` if llama becomes a default.
- Same caveat as the parent experiment: 7B sampling variance means single
  runs differ; these are 5-run aggregates, directionally consistent but
  not statistical proof.
