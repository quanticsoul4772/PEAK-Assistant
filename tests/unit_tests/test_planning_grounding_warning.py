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

"""Pins for the GROUNDING warning in the planning CLI loop (fork fix, finding 10).

After ``extract_hunt_plan``, the CLI runs the deterministic grounding checks
(``peak_assistant.utils.plan_grounding.check_plan_grounding``) over the plan +
discovery texts and prints a ``GROUNDING WARNING`` when the plan cites
undiscovered indices or non-executable SPL. The warning is loud but
non-blocking, matching the established fail-loud-not-fail-open pattern.

These tests call the CLI's ``main()`` with the agent team mocked out, so they
exercise the real argument parsing, file loading, extraction, and warning
emission.
"""

from __future__ import annotations

import io
import os
import tempfile
from contextlib import redirect_stdout
from unittest.mock import patch


from peak_assistant.planning_assistant.__main__ import main

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

DISCOVERY = "Discovered indices: winrm_hunt, _audit, main"


def _write_tmp(name: str, content: str) -> str:
    d = os.path.join(tempfile.gettempdir(), "peak-grounding-test")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def _run_cli(monkeypatch, plan: str, discovery_path: str) -> str:
    """Run planning main() with the agent team mocked; return captured stdout."""
    research_path = _write_tmp("research.md", "research body")

    monkeypatch.setattr(
        "sys.argv",
        [
            "planning-assistant",
            "-y", "test hypothesis",
            "-r", research_path,
            "-d", discovery_path,
            "--no-feedback",
        ],
    )

    # Mock the agent team: plan_hunt returns a TaskResult stand-in whose
    # extraction the CLI then performs. We patch extract_hunt_plan to return
    # the canned plan so the test focuses on the warning path.
    async def fake_plan_hunt(**kwargs):  # noqa: ANN003
        class _FakeResult:
            messages: list = []

        return _FakeResult()

    monkeypatch.setattr(
        "peak_assistant.planning_assistant.__main__.plan_hunt", fake_plan_hunt
    )
    monkeypatch.setattr(
        "peak_assistant.planning_assistant.__main__.extract_hunt_plan",
        lambda result: plan,
    )

    # --no-feedback breaks out of the loop; no SystemExit expected, but guard
    # against accidental input() by patching it to raise if reached.
    with patch("builtins.input", side_effect=AssertionError("input() reached")):
        buf = io.StringIO()
        with redirect_stdout(buf):
            main()
    return buf.getvalue()


def test_grounding_warning_printed_for_undiscovered_index_and_bad_spl(
    monkeypatch,
) -> None:
    discovery_path = _write_tmp("discovery-bad.md", DISCOVERY)
    out = _run_cli(monkeypatch, UNGROUNDED_PLAN, discovery_path)
    assert "GROUNDING WARNING" in out
    assert "netflow" in out
    assert "Not executable as written" in out
    assert "FROM_UNIXTIME" in out


def test_no_warning_for_grounded_plan(monkeypatch) -> None:
    discovery_path = _write_tmp("discovery-good.md", DISCOVERY)
    out = _run_cli(monkeypatch, GROUNDED_PLAN, discovery_path)
    assert "GROUNDING WARNING" not in out
    assert "Hunt plan:" in out
