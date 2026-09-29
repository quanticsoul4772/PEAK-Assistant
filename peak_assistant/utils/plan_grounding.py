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

"""Deterministic grounding checks for generated hunt plans (fork fix).

Finding 10 (2026-09-29): on the grounded-Splunk H1 run the planner cited
indices the discovery report had explicitly reported absent (``netflow``,
``audit``, ``endpoint``) and produced non-executable SPL (``tstats count ...
FROM_UNIXTIME(_time) ... WHERE _time > earliest``). The plan critic approved
both. One of six plan queries was executable; it matched zero events.

These helpers give the critic (and tests) a deterministic view of the same
defects, independent of model judgment:

- ``extract_spl_queries`` pulls candidate SPL statements from a plan's fenced
  code blocks.
- ``check_plan_indices`` reports index= tokens that do not appear in the
  discovery report.
- ``check_plan_spl_syntax`` reports statements that violate the pinned
  executable-SPL rules (placeholder time ranges, FROM_UNIXTIME inside
  tstats, bracketed elisions).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

_FENCED_BLOCK = re.compile(r"```(?:spl|splunk)?[ \t]*\r?\n(.*?)```", re.S)
_INDEX_TOKEN = re.compile(r"\bindex=([A-Za-z0-9_.\-]+)")
# Placeholder time predicates: "WHERE _time > earliest", "_time > earliest",
# "WHERE _time > <...>" style pseudocode.
_PLACEHOLDER_TIME = re.compile(
    r"_time\s*(?:>|>=|<|<=|=)\s*(?:earliest|latest)(?![A-Za-z0-9_])", re.I
)
# Bracketed elisions like "[rest of the query]" / "[...]" inside a statement.
_ELISION = re.compile(r"\[\s*(?:rest of|more|etc|\.{3}|\u2026)", re.I)
# FROM_UNIXTIME anywhere in a tstats pipeline is invalid Splunk.
_TSTATS_FROM_UNIXTIME = re.compile(r"\|\s*tstats\b[^|]*FROM_UNIXTIME", re.I)


@dataclass
class PlanGroundingReport:
    """Result of the deterministic plan checks."""

    plan_indices: List[str] = field(default_factory=list)
    undiscovered_indices: List[str] = field(default_factory=list)
    suspicious_queries: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.undiscovered_indices and not self.suspicious_queries


def extract_spl_queries(plan_text: str) -> List[str]:
    """Return non-empty SPL statements from the plan's fenced code blocks.

    Blocks fenced with ```spl/```splunk or bare ``` are all considered; the
    heuristics below key off SPL shapes (index=, |) so prose in a bare fence
    is not misclassified.
    """
    queries: List[str] = []
    for match in _FENCED_BLOCK.finditer(plan_text or ""):
        statement = " ".join(match.group(1).split())
        if not statement:
            continue
        if "index=" in statement.lower() or "|" in statement:
            queries.append(statement)
    return queries


def check_plan_indices(plan_text: str, discovery_text: str) -> List[str]:
    """Return index names used in the plan but absent from the discovery text.

    Comparison is case-insensitive. A plan index counts as discovered if the
    discovery report mentions it anywhere (its index tables quote the names),
    so plain substring membership is the intended, conservative test.
    """
    discovery_lower = (discovery_text or "").lower()
    undiscovered: List[str] = []
    for match in _INDEX_TOKEN.finditer(plan_text or ""):
        index_name = match.group(1).lower()
        if index_name and index_name not in discovery_lower and index_name not in undiscovered:
            undiscovered.append(index_name)
    return undiscovered


def check_plan_spl_syntax(plan_text: str) -> List[str]:
    """Return plan queries that violate the pinned executable-SPL rules."""
    suspicious: List[str] = []
    for query in extract_spl_queries(plan_text):
        problems = False
        if _PLACEHOLDER_TIME.search(query):
            problems = True
        if _ELISION.search(query):
            problems = True
        if _TSTATS_FROM_UNIXTIME.search(query):
            problems = True
        if problems and query not in suspicious:
            suspicious.append(query)
    return suspicious


def check_plan_grounding(plan_text: str, discovery_text: str) -> PlanGroundingReport:
    """Run all deterministic grounding checks; returns a report dataclass."""
    return PlanGroundingReport(
        plan_indices=[
            m.group(1) for m in _INDEX_TOKEN.finditer(plan_text or "")
        ],
        undiscovered_indices=check_plan_indices(plan_text, discovery_text),
        suspicious_queries=check_plan_spl_syntax(plan_text),
    )
