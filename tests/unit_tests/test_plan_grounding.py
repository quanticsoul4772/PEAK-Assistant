# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Pins for the deterministic plan-grounding checks (fork fix, finding 10).

The live grounded-Splunk H1 run produced a plan that cited indices the
discovery report had reported absent and non-executable SPL that the plan
critic approved. These tests pin the deterministic checks against the exact
failure shapes observed in that run.
"""

from __future__ import annotations

from peak_assistant.utils.plan_grounding import (
    check_plan_grounding,
    check_plan_indices,
    check_plan_spl_syntax,
    extract_spl_queries,
)

DISCOVERY = """
| Potential Splunk Indices/Data Sources | Description | Key Fields |
|---------------------------------------|-------------|-----------|
| `winrm_hunt` | Windows Security and Sysmon logs | `EventID`, `Computer`, `User` |
| `_audit` | Splunk audit events | `action`, `user` |
| `main` | Generic events | `host` |
"""


def test_extracts_queries_from_spl_and_splunk_fences() -> None:
    plan = "```spl\nindex=winrm_hunt | stats count\n```\nprose\n```splunk\nindex=main | head 10\n```"
    queries = extract_spl_queries(plan)
    assert len(queries) == 2
    assert queries[0] == "index=winrm_hunt | stats count"


def test_fence_tags_match_case_insensitively() -> None:
    """Regression: models emit case-variant fences (llama3.1:8b wrote 24
    blocks as ```sPL in a 5-run head-to-head); extraction must not miss
    them. Content rules are unchanged.
    """
    plan = (
        "```sPL\nindex=winrm_hunt | stats count\n```\n"
        "prose\n"
        "```SPL\nindex=winrm_hunt | head 10\n```\n"
        "```Spl\nindex=winrm_hunt | stats count by host\n```"
    )
    queries = extract_spl_queries(plan)
    assert len(queries) == 3
    assert all("index=winrm_hunt" in q for q in queries)

    # The extracted queries still flow through the deterministic checks.
    assert check_plan_indices(plan, DISCOVERY) == []


def test_undiscovered_index_is_flagged() -> None:
    plan = "```spl\nindex=netflow | stats count\n```"
    assert check_plan_indices(plan, DISCOVERY) == ["netflow"]


def test_discovered_indices_pass() -> None:
    plan = "```spl\nindex=winrm_hunt earliest=-24h | stats count by Computer\n```"
    assert check_plan_indices(plan, DISCOVERY) == []


def test_index_match_is_case_insensitive() -> None:
    plan = "```spl\nindex=WinRM_Hunt | stats count\n```"
    assert check_plan_indices(plan, DISCOVERY) == []


def test_placeholder_time_range_is_flagged() -> None:
    """The exact invalid shape from the live run."""
    plan = (
        "```spl\nindex=winrm_hunt | tstats count by sourcetype "
        "WHERE _time > earliest AND _time < latest\n```"
    )
    assert len(check_plan_spl_syntax(plan)) == 1


def test_tstats_from_unixtime_is_flagged() -> None:
    plan = "```spl\n| tstats count FROM_UNIXTIME(_time) by sourcetype\n```"
    assert len(check_plan_spl_syntax(plan)) == 1


def test_bracketed_elision_is_flagged() -> None:
    plan = "```spl\nindex=winrm_hunt | stats count [rest of the query]\n```"
    assert len(check_plan_spl_syntax(plan)) == 1


def test_valid_executable_query_passes_all_checks() -> None:
    plan = "```spl\nindex=winrm_hunt earliest=-24h latest=now | stats count by Computer\n```"
    assert check_plan_spl_syntax(plan) == []
    assert check_plan_indices(plan, DISCOVERY) == []


def test_full_report_shape_on_the_live_failure_reproduction() -> None:
    """A minimal reconstruction of the live H1 plan failures."""
    plan = (
        "1. Network\n```spl\nindex=netflow | tstats count FROM_UNIXTIME(_time) by sourcetype "
        "WHERE _time > earliest\n```\n"
        "2. Process\n```spl\nindex=winrm_hunt earliest=-24h | stats count by Computer\n```"
    )
    report = check_plan_grounding(plan, DISCOVERY)
    assert report.undiscovered_indices == ["netflow"]
    assert len(report.suspicious_queries) == 1
    assert "winrm_hunt" in report.plan_indices
    assert report.ok is False


def test_clean_plan_reports_ok() -> None:
    plan = "```spl\nindex=winrm_hunt earliest=-24h latest=now | stats count by Computer\n```"
    report = check_plan_grounding(plan, DISCOVERY)
    assert report.ok is True
    assert report.undiscovered_indices == []
    assert report.suspicious_queries == []
