# Fork Branch Audit — keep / merge / delete

**Audited:** 2026-09-26. **Scope:** all 34 branches on
`quanticsoul4772/PEAK-Assistant` (the fork). **Method:** SHA comparison against
`Cisco-Talos/PEAK-Assistant` (read-only), `git merge-base --is-ancestor` vs
`main`, `git cherry` patch-equivalence vs `main`, upstream PR history (read-only).
**Status: categories A + B + C (21 branches) deleted from the fork on
2026-09-26.** Category D (11 harvest candidates) remains pending the
decision below. All deleted branches still exist on upstream — nothing lost.

## TL;DR — origin of the noise

**None of the 33 stray branches are ours.** They were copied from
`Cisco-Talos/PEAK-Assistant` at fork time (GitHub copies every branch). All are
authored by **DavidJBianco / David J. Bianco** (the PEAK maintainer), committed
2025-10 → 2026-05, and every SHA matches upstream exactly. They mirror his
reviewed-but-unmerged agent-generated fixes (`codex/*`) and his merged
consolidation batches (`batch-*`).

Only branches that are ours: `main` (contains merged PR #1) and `notes/research`.

Because every branch still exists on upstream (and in our local `upstream/*`
remote-tracking refs), **deleting our copies loses nothing permanently.**

## Classification

### A. DELETE — already merged into `main` (10 branches, zero unique content)

`git merge-base --is-ancestor` confirms each is contained in `main`;
`git rev-list --count main..<branch>` = 0.

| Branch | Note |
|---|---|
| `batch-a-quick-fixes` | merged via upstream PR #84 |
| `batch-b-auth-contract` | merged via PR #85 |
| `batch-b-context-file` | merged via PR #86 |
| `batch-c-logging-opt-in` | merged via PR #87 |
| `batch-d-refiner-fixes` | merged via PR #88 |
| `codex/fix-full-message-logging-vulnerability` | absorbed (patch in main) |
| `dev` | == old main tip |
| `feature/azure-model-info` | merged earlier |
| `fix/issue-69-runner-source-labels` | merged earlier |
| `flex-provider` | merged earlier |

### B. DELETE — fix already in `main` via the batch consolidations (9 branches)

`git cherry main` marks these `-` (patch-equivalent commit already in main):

| Branch | Absorbed by |
|---|---|
| `codex/fix-authentication-bypass-in-mcp-server` | batch-b (PR #85) |
| `codex/fix-local-context-information-disclosure` | batch-b (PR #86) |
| `codex/fix-mcp-hypothesizer-argument-order` | batch consolidations |
| `codex/fix-mutable-default-for-previous_run` | batch-d (PR #88) |
| `codex/fix-session-key-reset-in-data-discovery` | batch consolidations |
| `codex/fix-stdio-timeout-conversion-crash` | batch consolidations |
| `codex/fix-unvalidated-url-checks-in-evaluator` | batch-a (PR #84) |
| `codex/propose-fix-for-command-injection-vulnerability` | batch consolidations |
| `codex/propose-fix-for-logging-vulnerability-9zt7m3` | batch-c (PR #87) |

### C. DELETE — live upstream PRs; fork copies serve no purpose (2 branches)

| Branch | Upstream PR | State |
|---|---|---|
| `codex/fix-able-table-endpoint-importerror` | #90 "Fix ABLE feedback UserMessage import" | OPEN upstream |
| `codex/propose-fix-for-process-env-leak` | #91 "fix: restrict Streamlit MCP test subprocess env" | OPEN upstream |

If these merge upstream, a fork sync delivers them. Keep no local copies.

### D. HARVEST-then-DELETE — fixes absent from `main`, upstream PRs closed unmerged (11 branches)

**Post-review correction (2026-09-26, see PR #3):** `git cherry` measures
*patch* equivalence only. When the 7 high-value candidates were cherry-picked
for review, **5 turned out semantically superseded** by main's June dev merge
(PR #92) and were dropped: the Dockerfile fix (main copies Node 20 from the
official `node:20-slim` image), the auth_module restriction (main has a
deny-by-default `PEAK_AUTH_MODULE_ALLOWLIST`), the logging fix (main threads
`debug_agents: bool = False`), the context.txt fix (main's code is identical),
and the refiner error handling (main's try/except is a superset). **Only 2 were
genuinely missing** and are harvested in PR #3: the `.env` CWD-only hardening
and the HTTP MCP auth failure check. The CI/registry four were not evaluated.

These are real fixes the maintainer's Codex runs proposed and **closed without
merging** (PRs #54–#83 series). `git cherry` says their patches are NOT in main.
Since our fork is now our own product, these are free to take — but each was
reviewed-and-not-merged upstream, so **read before you take**.

**High value for our roadmap (hypothesis phase / MCP / runtime):**

| Branch | Upstream PR | Why it matters to us |
|---|---|---|
| `codex/fix-unhandled-exception-in-hypothesis-refiner-cli` | #77 | refiner CLI crash on agent failure — we build in the hypothesis phase |
| `codex/fix-http-mcp-auth-connection-issue` | #71 | HTTP MCP auth failure handling — we add MCP servers |

**Security hardening (worth taking for a fork meant to run locally with real keys):**

| Branch | Upstream PR |
|---|---|
| `codex/fix-untrusted-.env-discovery-vulnerability` | #63 (harden `.env` discovery to CWD) |
| `codex/propose-fix-for-auth-module-vulnerability` | #65 (restrict `auth_module` imports) |
| `codex/fix-vulnerability-in-dockerfile-with-remote-script` | #61 (no remote NodeSource script) |
| `codex/propose-fix-for-local-context-leak` | #75 (context.txt auto-injection) |
| `codex/propose-fix-for-logging-vulnerability` | #72 (callback tracing off by default) |

**CI/registry hardening (only matters if the fork ever publishes container images):**

| Branch | Upstream PR |
|---|---|
| `codex/fix-ci-merge-job-vulnerability` | — (no PR found in list window) |
| `codex/fix-ci-workflow-to-restrict-image-pushes` | #60 |
| `codex/fix-manifest-push-security-vulnerability` | #58 |
| `codex/propose-fix-for-ci-workflow-vulnerability` | #57 |

## Recommendations

1. ~~**Delete categories A + B + C now (21 branches).**~~ **Done 2026-09-26**
   (verified: fork now has exactly `main`, `notes/research`, and the 11
   category-D branches).
2. ~~**Harvest category D (7 branches: "high value" + "security hardening") into a
   `fork-maintenance` branch**~~ **Done 2026-09-26 (PR #3) — outcome: 2 taken,
   5 dropped as superseded (see correction above).** All remaining category-D
   branches can now be deleted too: the 2 harvested fixes live on
   `fork-maintenance`.
3. **Delete the remaining D branches after harvest** (or immediately if you
   decide not to take any — they live on upstream regardless).
4. **Never push any of this upstream.** Fork-only policy applies (README).

### Commands (not executed — for when you decide)

```bash
# A + B + C (21 branches):
for b in batch-a-quick-fixes batch-b-auth-contract batch-b-context-file \
  batch-c-logging-opt-in batch-d-refiner-fixes \
  codex/fix-full-message-logging-vulnerability dev feature/azure-model-info \
  fix/issue-69-runner-source-labels flex-provider \
  codex/fix-authentication-bypass-in-mcp-server \
  codex/fix-local-context-information-disclosure \
  codex/fix-mcp-hypothesizer-argument-order \
  codex/fix-mutable-default-for-previous_run \
  codex/fix-session-key-reset-in-data-discovery \
  codex/fix-stdio-timeout-conversion-crash \
  codex/fix-unvalidated-url-checks-in-evaluator \
  codex/propose-fix-for-command-injection-vulnerability \
  codex/propose-fix-for-logging-vulnerability-9zt7m3 \
  codex/fix-able-table-endpoint-importerror \
  codex/propose-fix-for-process-env-leak; do
  git push origin --delete "$b"
done

# Harvest example (review each before committing):
git switch -c fork-maintenance main
git cherry-pick origin/codex/fix-unhandled-exception-in-hypothesis-refiner-cli
# ... review, test, then push and open a PR on the fork.
```

## Provenance

- Fork: `quanticsoul4772/PEAK-Assistant`, `main` = `c505cd9` (PR #1 merged
  2026-09-26), `notes/research` active.
- Upstream branch/PR inspection was strictly read-only (ls-remote, pr list).
- Classification tools: `git merge-base --is-ancestor`, `git rev-list --count`,
  `git cherry` (patch-id), upstream PR titles #54–#91.
