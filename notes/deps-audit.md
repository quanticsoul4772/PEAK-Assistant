# Dependency CVE Audit — PEAK fork (Python lockfile)

**Audited:** 2026-09-26 (point-in-time). **Remediated:** 2026-09-27 (Tiers 1–2
done; Tier 3 targets corrected below). **Scope:** all pinned packages in
`uv.lock` (exported via `uv export --all-groups` — the exact pins `uv sync`
installs). **Source:** OSV.dev advisory database (batch query + per-advisory
detail), cross-checked with PyPI for release metadata. Every reported advisory
was verified to affect the pinned version (affected-range check; all
"unconfirmed=0").

**Method note:** `pip-audit` (2.10.1) was the intended tool but hung repeatedly
on its per-package service calls in this environment (even with `--no-deps`);
the audit was completed with the same underlying data source (OSV) via a batch
query. Scratch scripts live in `.git/` and are not committed.

> **Correction (2026-09-27):** the original "Min fixed" column listed, per
> package, the *earliest* release that fixes *any* of its advisories — not the
> release that clears *all* of them. Locking to those versions and re-auditing
> still flagged 7 of 11 Tier 1 packages (e.g. `aiohttp` 3.13.3 carried 48
> remaining advisories). The **"Min safe"** column below is the minimum release
> with **zero** applicable advisories, verified per version against OSV. Where
> the two differ, the old value is shown in notes. The old table also omitted
> `lxml` entirely.

## Status

| Checkpoint | Pins | Affected pkgs | Advisories | Tier 1 | Tier 2 |
|---|---|---|---|---|---|
| 2026-09-26 baseline | 155 | 30 | 295 | 11 pkgs / 140 adv | 2 pkgs / 25 adv |
| after Tier 1 (PR #5) | 158 | 19 | 155 | **0** | 2 pkgs / 25 adv |
| after Tier 2 (this PR) | 158 | 17 | 130 | **0** | **0** |

The remaining 17 packages / 130 advisories are all Tier 3 (plus `diskcache`,
which has no fix). The pin count rose 155→158 because `mcp` 1.28.1 needs
`pydantic` 2.13.x while the autogen stack stays on 2.11.x — the lock now
carries both `pydantic`/`pydantic-core`/`typing-inspection` lines (harmless).

## Tier 1 — network/auth-facing (DONE, PR #5)

These handle credentials, TLS, HTTP, or MCP traffic. All upgraded to the
minimum safe version; every one re-audits at zero advisories.

| Package | Was | Adv | Min safe | Applied | Notes |
|---|---|---|---|---|---|
| `cryptography` | 45.0.7 | 13 | **50.0.0** | 50.0.0 | major jump required for zero advisories |
| `pyopenssl` | 25.3.0 | 4 | **26.4.0** | 26.4.0 | 26.4.0 is the only release accepting cryptography 50 |
| `pyjwt` | 2.10.1 | 13 | **2.13.0** | 2.13.0 | |
| `mcp` | 1.14.0 | 6 | **1.28.1** | 1.28.1 | stays on 1.x; 2.x major deferred |
| `python-dotenv` | 1.1.1 | 2 | **1.2.2** | 1.2.2 | |
| `aiohttp` | 3.12.15 | 64 | **3.14.3** | 3.14.3 | |
| `urllib3` | 2.5.0 | 8 | **2.7.0** | 2.7.0 | |
| `requests` | 2.32.5 | 2 | **2.33.0** | 2.33.0 | |
| `starlette` | 0.48.0 | 12 | **1.3.1** | 1.3.1 | major (0.x→1.x) |
| `python-multipart` | 0.0.20 | 14 | **0.0.31** | 0.0.31 | |
| `snowflake-connector-python` | 3.17.3 | 2 | **4.7.1** | 4.7.1 | 4.0.0–4.7.0 still carry 2 advisories |

Forced collateral: `snowflake-snowpark-python` 1.38.0→1.41.0 (first release
allowing connector 4.x), `cffi` 1.17.1→2.1.1 (cryptography 50 requires
cffi 2.x).

### Conflict chains (verified with isolated resolver probes)

1. **The snowflake stack caps pyopenssl.** Chain:
   `streamlit-extras[pandas] 0.7.8` → `altex` → `snowflake-snowpark-python`
   → `snowflake-connector-python` → `pyopenssl`. `snowpark` 1.38.0–1.40.x cap
   `snowflake-connector-python<4.0.0`, and connector 3.18.x caps
   `pyopenssl>=22,<26` — so the old table's pair (connector 3.18.1 +
   pyopenssl 26.0.0) is **unsatisfiable**. Connector must leave the 3.x line:
   4.0.0–4.7.0 still carry 2 advisories, **4.7.1** is the first clean 4.x,
   and `snowpark` **1.41.0** is the first release that permits connector 4.x.
2. **pyopenssl caps cryptography.** 26.0.0–26.3.0 cap cryptography `<47`,
   `<48`, `<49`, `<50` respectively; **26.4.0** (`>=49,<51`) is the only
   release compatible with cryptography 50.0.0.
3. `mcp` 1.28.1 requires `pydantic` 2.13.x; autogen pins 2.11.x — dual
   pydantic lines in the lock, no functional impact.
4. `streamlit-extras` 0.7.8 only requires `streamlit>=1.37.0` (no upper cap),
   so Tier 2 did not disturb the snowflake stack.

## Tier 2 — web UI surface (DONE, this PR)

| Package | Was | Adv | Min safe | Applied | Notes |
|---|---|---|---|---|---|
| `streamlit` | 1.49.1 | 4 | **1.54.0** | 1.54.0 | old table said 1.53.1 — still carries 2 advisories |
| `tornado` | 6.5.2 | 21 | **6.5.8** | 6.5.8 | old table said 6.5.3 — still carries 15 advisories |

Boot smoke verified 2026-09-27: headless `streamlit run
peak_assistant/streamlit/app.py` on 1.54.0 serves `/_stcore/health` ok and the
root page 200. Streamlit minors occasionally change widget behavior — a manual
chat/OAuth click-through is still recommended before production use.

## Tier 3 — transitive / tooling (pending)

Not on the credential path. Old "Min fixed" values (earliest fix) were wrong
for five rows; corrected targets below.

| Package | Pinned | Adv | Min safe | Latest | Notes |
|---|---|---|---|---|---|
| `gitpython` | 3.1.45 | 55 | **3.1.60** | 3.1.62 | old said 3.1.47 |
| `pillow` | 11.3.0 | 36 | **12.3.0** | 12.3.0 | major; old said 12.1.1 |
| `pymdown-extensions` | 10.16.1 | 6 | **11.0.1** | 12.1 | major; old said 10.21.3 |
| `soupsieve` | 2.8 | 6 | **2.9** | 2.10 | old said 2.8.4 (not a release) |
| `filelock` | 3.19.1 | 4 | **3.20.3** | 4.0.4 | old said 3.20.1 |
| `lxml` | 6.0.1 | 2 | **6.1.0** | 6.1.3 | omitted from the old table |
| `protobuf` | 5.29.5 | 2 | **5.29.6** | 7.36.2 | |
| `pyarrow` | 21.0.0 | 2 | **23.0.1** | 25.0.1 | major |
| `pygments` | 2.19.2 | 2 | **2.20.0** | 2.21.0 | |
| `fonttools` | 4.60.0 | 2 | **4.60.2** | 4.66.0 | |
| `idna` | 3.10 | 2 | **3.15** | 3.20 | |
| `anyio` | 4.10.0 | 2 | **4.14.2** | 4.15.1 | |
| `click` | 8.2.1 | 1 | **8.3.3** | 8.5.0 | |
| `setuptools` | 80.9.0 | 2 | **83.0.0** | 84.0.0 | |
| `wheel` | 0.45.1 | 2 | **0.46.2** | 0.48.0 | |
| `pytest` (dev) | 8.4.2 | 2 | **9.0.3** | 9.1.1 | dev-only major |
| `diskcache` | 5.6.3 | 2 | **none** | 5.6.3 | no fix — accepted risk, see below |

### Accepted risk: `diskcache` 5.6.3

Recorded 2026-09-27 (remediation plan item 4). **Accept-and-monitor.**
`diskcache` 5.6.3 is the latest release; its 2 advisories are local attack
surface (AV:L, user interaction) on the caching path only — not the credential
path. Revisit when a fixed release ships, or replace/vendor a patch if cache
contents become sensitive.

## Remediation plan

1. ~~**Tier 1 first**~~ — **done** (PR #5, merged 2026-09-27): all 11 packages
   at min-safe, re-audits at zero. `mcp` stayed on 1.x (2.x major deferred).
2. ~~**Tier 2**~~ — **done** (this PR): `streamlit` 1.54.0 + `tornado` 6.5.8,
   boot smoke green, re-audits at zero.
3. **Tier 3:** batch `uv lock --upgrade-package <pkg>==<min safe>` to the
   targets above, `uv sync`, full test suite, re-audit. `pytest` 8→9,
   `pillow` 11→12, `pyarrow` 21→23, `pymdown-extensions` 10→11 are majors —
   gate on the suite. (Suggest bundling with the next routine upgrade pass.)
4. ~~**`diskcache`**~~ — **accepted risk recorded** (above).
5. **Cadence:** re-run this audit quarterly and before any release/tag.

## Verification record (2026-09-27)

- `uv run pytest -m "not live"`: baseline 4 failed / 208 passed →
  **215 passed / 1 skipped** (the 4 pre-existing Windows failures fixed:
  3 tempdir-cwd teardown bugs in `test_streamlit_helpers_mcp_bugs.py`, and
  `test_temp_file_is_owner_readable_only` now asserts a DACL check on Windows,
  where POSIX mode bits cannot be expressed)
- `uv run ruff check .`: 88 errors (pre-existing debt, unchanged)
- `uv run mypy .`: 3 errors (pre-existing debt, unchanged)
- OSV re-audit after both tiers: 17 pkgs / 130 advisories, Tier 1 + Tier 2
  zero (numbers in the Status table)

## Context

- This lockfile originally tracked upstream's June merge. `pyproject.toml`
  floors are now bumped for the direct deps:
  `python-dotenv>=1.2.2`, `mcp>=1.28.1`, `aiohttp>=3.14.3`, `streamlit>=1.54.0`.
- The fork runs local-first with real keys coming soon; Tier 1 packages are
  precisely the ones that will touch those keys (TLS stack, JWT, HTTP clients,
  `.env` loading, MCP transport) — now at zero advisories.
