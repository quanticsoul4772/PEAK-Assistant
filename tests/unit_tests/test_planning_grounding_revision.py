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

"""Pins for the grounding revision round in ``plan_hunt`` (fork fix, finding 10).

When the first plan fails the deterministic grounding checks, ``plan_hunt``
feeds the specific violations back as a user message and runs the team once
more. These tests pin: revision happens exactly when grounding fails, the
feedback names the violations, and a grounded first plan runs a single round.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

import pytest

from peak_assistant.planning_assistant import plan_hunt

UNGROUNDED_PLAN = (
    "1. Network\n"
    "```spl\n"
    "index=netflow | tstats count FROM_UNIXTIME(_time) by sourcetype "
    "WHERE _time > earliest\n"
    "```\n"
)

GROUNDED_PLAN = (
    "```spl\n"
    "index=winrm_hunt earliest=-24h latest=now | stats count by Computer\n"
    "```\n"
)

REVISED_PLAN = (
    "```spl\n"
    "index=winrm_hunt earliest=-24h latest=now | stats count by Computer, User\n"
    "```\n"
)

DISCOVERY = "Discovered indices: winrm_hunt, _audit, main"


@dataclass
class _Msg:
    source: str
    content: str


@dataclass
class _Result:
    messages: List[Any] = field(default_factory=list)
    stop_reason: str = ""


class _RecordingTeam:
    """RoundRobinGroupChat stand-in that returns scripted results and records
    the task messages of each run."""

    def __init__(self, participants, termination_condition):
        self.participants = participants
        self.termination_condition = termination_condition
        self.tasks: List[List[_Msg]] = []

    async def run(self, task=None, **kwargs):
        # Scripting keys off the number of completed runs: the recording
        # subclasses append the incoming task to self.tasks BEFORE delegating
        # here, so len(self.tasks)-1 is the current run's zero-based index.
        run_index = len(self.tasks) - 1 if self.tasks else 0
        if run_index == 0:
            # First round: planner produces an ungrounded plan, critic echoes
            # the terminator (as it would after approving).
            return _Result(
                messages=[
                    _Msg("hunt_planner", UNGROUNDED_PLAN),
                    _Msg("hunt_plan_critic", "approved YYY-TERMINATE-YYY"),
                ],
                stop_reason="Text 'YYY-TERMINATE-YYY' mentioned",
            )
        # Revision round: grounded plan.
        return _Result(
            messages=[
                _Msg("hunt_planner", REVISED_PLAN),
                _Msg("hunt_plan_critic", "approved YYY-TERMINATE-YYY"),
            ],
            stop_reason="Text 'YYY-TERMINATE-YYY' mentioned",
        )


class _PassThroughConsole:
    @staticmethod
    async def run_stream(task=None, output_stats=False):
        raise AssertionError("verbose path not exercised in these tests")


@pytest.mark.asyncio
async def test_revision_round_runs_when_first_plan_is_ungrounded(monkeypatch):
    """Ungrounded first plan -> one revision round with violation feedback."""
    runs: List[List[_Msg]] = []

    class _Team(_RecordingTeam):
        async def run(self, task=None, **kwargs):
            self.tasks.append(list(task or []))
            runs.append(list(task or []))
            return await _RecordingTeam.run(self, task=task, **kwargs)

    async def fake_get_model_client(agent_name=None, **kwargs):
        return object()


    monkeypatch.setattr(
        "peak_assistant.planning_assistant.get_model_client", fake_get_model_client
    )
    monkeypatch.setattr(
        "peak_assistant.planning_assistant.RoundRobinGroupChat", _Team
    )
    monkeypatch.setattr(
        "peak_assistant.planning_assistant.Console", _PassThroughConsole
    )
    calls = []

    def fake_extract(result):
        content = result.messages[0].content if result.messages else ""
        calls.append(content)
        return UNGROUNDED_PLAN if content == UNGROUNDED_PLAN else REVISED_PLAN

    monkeypatch.setattr(
        "peak_assistant.planning_assistant.extract_hunt_plan", fake_extract
    )
    monkeypatch.setattr(
        "peak_assistant.planning_assistant.check_plan_grounding",
        lambda plan, discovery: __import__(
            "peak_assistant.utils.plan_grounding", fromlist=["check_plan_grounding"]
        ).check_plan_grounding(plan, discovery),
    )

    result = await plan_hunt(
        research_document="research",
        local_data_document="",
        hypothesis="hyp",
        able_info="able",
        data_discovery=DISCOVERY,
        local_context="",
    )

    assert len(runs) == 2, (
        f"expected 2 team runs, got {len(runs)}; extract calls={calls!r}"
    )
    # The second run's task must carry the grounding feedback message.
    feedback_msgs = [
        m for m in runs[1] if "GROUNDING REVISION REQUIRED" in getattr(m, "content", "")
    ]
    assert feedback_msgs, "revision round missing the grounding feedback message"
    feedback = feedback_msgs[0].content
    assert "netflow" in feedback
    assert "FROM_UNIXTIME" in feedback
    assert any(m.content == REVISED_PLAN for m in result.messages)


@pytest.mark.asyncio
async def test_single_round_when_first_plan_is_grounded(monkeypatch):
    """Grounded first plan -> exactly one team run, no revision feedback."""
    runs: List[List[_Msg]] = []

    class _Team(_RecordingTeam):
        async def run(self, task=None, **kwargs):
            self.tasks.append(list(task or []))
            runs.append(list(task or []))
            return _Result(
                messages=[
                    _Msg("hunt_planner", GROUNDED_PLAN),
                    _Msg("hunt_plan_critic", "approved YYY-TERMINATE-YYY"),
                ],
                stop_reason="Text 'YYY-TERMINATE-YYY' mentioned",
            )

    async def fake_get_model_client(agent_name=None, **kwargs):
        return object()

    monkeypatch.setattr(
        "peak_assistant.planning_assistant.get_model_client", fake_get_model_client
    )
    monkeypatch.setattr(
        "peak_assistant.planning_assistant.RoundRobinGroupChat", _Team
    )
    monkeypatch.setattr(
        "peak_assistant.planning_assistant.Console", _PassThroughConsole
    )
    monkeypatch.setattr(
        "peak_assistant.planning_assistant.extract_hunt_plan",
        lambda result: GROUNDED_PLAN,
    )

    result = await plan_hunt(
        research_document="research",
        local_data_document="",
        hypothesis="hyp",
        able_info="able",
        data_discovery=DISCOVERY,
        local_context="",
    )

    assert len(runs) == 1, f"grounded plan must run once, got {len(runs)}"
    assert any(m.content == GROUNDED_PLAN for m in result.messages)
