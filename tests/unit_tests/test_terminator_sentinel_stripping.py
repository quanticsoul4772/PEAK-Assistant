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

"""Pins for terminator-sentinel stripping from stage outputs (fork fix).

Observed live during the grounded-Splunk H1 hunt: the discovery agent echoed
the literal string ``YYY-TERMINATE-YYY`` inside its report body (quoting its
own instruction). The planning stage's ``TextMentionTermination`` scans every
message — including the user-role message the discovery output becomes — so
the planning team terminated on its first input message (52 µs) and produced
"no plan was generated".

The fix: every sentinel is stripped from any string that passes through
``extract_agent_result``, so no stage output can carry a sentinel into the
next stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from autogen_agentchat.messages import TextMessage

from peak_assistant.utils.result_extractors import (
    TERMINATOR_SENTINELS,
    extract_agent_result,
    extract_data_discovery_report,
    strip_terminator_sentinels,
)


@dataclass
class _Msg:
    source: str
    content: str


@dataclass
class _Result:
    """Duck-typed TaskResult stand-in (Any keeps mypy quiet about the stub)."""

    messages: List[Any] = field(default_factory=list)


def test_strip_removes_every_known_sentinel() -> None:
    text = "a YYY-TERMINATE-YYY b YYY-HYPOTHESIS-ACCEPTED-YYY c"
    assert strip_terminator_sentinels(text) == "a  b  c"


def test_sentinel_registry_covers_both_live_sentinels() -> None:
    assert "YYY-TERMINATE-YYY" in TERMINATOR_SENTINELS
    assert "YYY-HYPOTHESIS-ACCEPTED-YYY" in TERMINATOR_SENTINELS


def test_extraction_strips_echoed_sentinel_from_discovery_report() -> None:
    """The exact live failure: discovery report body contains the sentinel."""
    report = (
        "# Discovery\n\n"
        "index=winrm_hunt queries...\n\n"
        "```splunk\nYYY-TERMINATE-YYY\n```\n"
    )
    result = _Result(messages=[_Msg("Data_Discovery_Agent", report)])
    cleaned = extract_agent_result(result, "data_discovery")  # type: ignore[arg-type]
    assert "YYY-TERMINATE" not in cleaned
    assert "index=winrm_hunt" in cleaned


def test_extraction_strips_foreign_sentinel_not_in_own_cleanup_list() -> None:
    """data_discovery's cleanup_patterns do not include the hypothesis
    sentinel — the central strip must remove it anyway (cross-stage echo)."""
    result = _Result(
        messages=[_Msg("Data_Discovery_Agent", "report YYY-HYPOTHESIS-ACCEPTED-YYY tail")]
    )
    cleaned = extract_data_discovery_report(result)  # type: ignore[arg-type]
    assert "YYY-HYPOTHESIS" not in cleaned


def test_string_passthrough_still_strips() -> None:
    """extract_agent_result returns str results directly; the strip must apply
    there too, since hypothesizer output rides the same path."""
    cleaned = extract_agent_result("analysis YYY-TERMINATE-YYY done", "data_discovery")
    assert "YYY-TERMINATE" not in cleaned


def test_taskresult_messages_strip() -> None:
    """Autogen TextMessage objects (duck-typed) flow through cleanly."""
    result = _Result(
        messages=[TextMessage(source="hunt_planner", content="plan YYY-TERMINATE-YYY end")]
    )  # type: ignore[arg-type]
    cleaned = extract_agent_result(result, "hunt_planner")  # type: ignore[arg-type]
    assert "YYY-TERMINATE" not in cleaned
    assert "plan" in cleaned and "end" in cleaned


def test_content_without_sentinel_is_unchanged() -> None:
    text = "normal report content with index=main"
    result = _Result(messages=[_Msg("Data_Discovery_Agent", text)])
    assert extract_agent_result(result, "data_discovery") == text  # type: ignore[arg-type]
