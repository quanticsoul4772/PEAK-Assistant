# Dependency CVE Audit — PEAK fork (Python lockfile)

**Audited:** 2026-09-26 (point-in-time). **Scope:** all 155 pinned packages in
`uv.lock` (exported via `uv export --all-groups` — the exact pins `uv sync`
installs). **Source:** OSV.dev advisory database (batch query + per-advisory
detail), cross-checked with PyPI for latest versions. Every reported advisory
was verified to affect the pinned version (affected-range check; all
"unconfirmed=0").

**Method note:** `pip-audit` (2.10.1) was the intended tool but hung repeatedly
on its per-package service calls in this environment (even with `--no-deps`);
the audit was completed with the same underlying data source (OSV) via a batch
query. Scratch scripts live in `.git/` and are not committed.

## Verdict

**30 of 155 pinned packages carry applicable advisories (295 total).** The
lockfile is materially behind on security patches — before real API keys are
configured, the network/auth-facing tier below should be upgraded first.

One package has **no fix available**: `diskcache==5.6.3` (2 advisories; latest
release is the pinned one).

## Tier 1 — network/auth-facing (upgrade before API keys)

These handle credentials, TLS, HTTP, or MCP traffic.

| Package | Pinned | Advisories | Min fixed | Latest | Worst severity |
|---|---|---|---|---|---|
| `cryptography` | 45.0.7 | 13 | **46.0.5** | 50.0.1 | AV:N C:H/I:H/A:H (critical-class) |
| `pyopenssl` | 25.3.0 | 4 | **26.0.0** | 26.4.0 | AV:N C:H/I:H/A:H |
| `pyjwt` | 2.10.1 | 13 | **2.12.0** | 2.15.0 | AV:N C:H/I:H |
| `mcp` | 1.14.0 | 6 | **1.23.0** | 2.2.0 | AV:N VC:H/VI:H |
| `python-dotenv` | 1.1.1 | 2 | **1.2.2** | 1.2.3 | C:N/I:H (env loading integrity) |
| `aiohttp` | 3.12.15 | 64 | **3.13.3** | 3.14.3 | AV:N C:H/I:N |
| `urllib3` | 2.5.0 | 8 | **2.6.0** | 2.8.0 | AV:N C:N/I:N/A:H |
| `requests` | 2.32.5 | 2 | **2.33.0** | 2.34.2 | I:H |
| `starlette` | 0.48.0 | 12 | **0.49.1** | 1.7.0 | AV:N C:H/I:N |
| `python-multipart` | 0.0.20 | 14 | **0.0.22** | 0.0.32 | C:L/I:H |
| `snowflake-connector-python` | 3.17.3 | 2 | **3.18.1** | 4.7.5 | AV:N VC:H/VI:H |

## Tier 2 — web UI surface

| Package | Pinned | Advisories | Min fixed | Latest | Notes |
|---|---|---|---|---|---|
| `streamlit` | 1.49.1 | 4 | **1.53.1** | 1.64.0 | the app's own UI |
| `tornado` | 6.5.2 | 21 | **6.5.3** | 6.5.10 | streamlit's web server |

## Tier 3 — transitive / tooling (lower priority for key safety)

| Package | Pinned | Advisories | Min fixed | Latest |
|---|---|---|---|---|
| `gitpython` | 3.1.45 | 55 | 3.1.47 | 3.1.62 |
| `pillow` | 11.3.0 | 36 | 12.1.1 | 12.3.0 |
| `pymdown-extensions` | 10.16.1 | 6 | 10.21.3 | 12.1 |
| `soupsieve` | 2.8 | 6 | 2.8.4 | 2.10 |
| `filelock` | 3.19.1 | 4 | 3.20.1 | 4.0.4 |
| `protobuf` | 5.29.5 | 2 | 5.29.6 | 7.36.2 |
| `pyarrow` | 21.0.0 | 2 | 23.0.1 | 25.0.1 |
| `pygments` | 2.19.2 | 2 | 2.20.0 | 2.21.0 |
| `fonttools` | 4.60.0 | 2 | 4.60.2 | 4.66.0 |
| `idna` | 3.10 | 2 | 3.15 | 3.20 |
| `anyio` | 4.10.0 | 2 | 4.14.2 | 4.15.1 |
| `click` | 8.2.1 | 1 | 8.3.3 | 8.5.0 |
| `setuptools` | 80.9.0 | 2 | 83.0.0 | 84.0.0 |
| `wheel` | 0.45.1 | 2 | 0.46.2 | 0.48.0 |
| `pytest` (dev) | 8.4.2 | 2 | 9.0.3 | 9.1.1 |
| `diskcache` | 5.6.3 | 2 | **none** | 5.6.3 |

`diskcache` has no fixed release — accept-and-monitor, replace, or vendor a
patch (decision needed).

## Remediation plan

1. **Tier 1 first:** `uv lock --upgrade-package <pkg>` for each Tier 1 package
   (to at least the "Min fixed" version), `uv sync`, full test suite, re-audit.
   Note `mcp` 1.23 → 2.x is a major bump; 1.23.0 clears the advisories without
   the major jump — prefer the minimum safe versions first, latest later.
2. **Tier 2:** bump `streamlit`/`tornado` and verify the UI smoke (chat, OAuth
   flows) manually — Streamlit minors occasionally change widget behavior.
3. **Tier 3:** batch `uv lock --upgrade` on a branch, run `make checks` + tests;
   `pytest` 8→9 is a dev-only major, gate on the suite.
4. **`diskcache`:** record the accepted risk in the fork's notes until a fixed
   release exists (it is not on the credential path — caching only).
5. **Cadence:** re-run this audit quarterly and before any release/tag.

## Context

- This lockfile tracks upstream's June merge; the pins reflect upstream's
  `pyproject.toml` constraints (e.g. `aiohttp>=3.12.15`, `mcp>=1.12.2`).
  Remediation may need `pyproject.toml` floor bumps for Tier 1 packages.
- The fork runs local-first with real keys coming soon; Tier 1 packages are
  precisely the ones that will touch those keys (TLS stack, JWT, HTTP clients,
  `.env` loading, MCP transport).
