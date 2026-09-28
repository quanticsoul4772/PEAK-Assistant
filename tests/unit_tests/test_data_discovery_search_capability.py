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

"""Pins for the data-discovery search-capability warning (fork fix).

Observed live during the H1/H5 hunt comparison: with only parallax's
corrective-memory tools in the ``data_discovery`` group, the discovery agent
fabricated a plausible Splunk index inventory (``security-alt.Event``,
``security_event``, ``powershell-remoting``) because its prompt demands it
"actually inspect the events in every index ... in Splunk" and no tool allowed
that. Planning then quoted the fabricated names back as ground truth.

These tests pin the deterministic warning that fires when the workbench has no
search-capable tools, and that it stays silent when one exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pytest

from peak_assistant.data_assistant import _warn_if_no_search_tools


@dataclass
class _FakeSchema:
    name: str


class _FakeWorkbench:
    def __init__(self, tool_names: List[str]) -> None:
        self._tools = [_FakeSchema(name=n) for n in tool_names]

    async def list_tools(self):
        # Match the real McpWorkbench: dict payloads with a "name" key.
        return [{"name": s.name} for s in self._tools]


@pytest.mark.asyncio
async def test_warning_fires_when_no_tool_can_search(capsys) -> None:
    """The parallax-tools-only shape must produce the loud UNVERIFIED warning."""
    workbench = _FakeWorkbench(
        ["check", "checkpoint_action", "checkpoint_batch", "checkpoint_turn",
         "decide", "diverge", "elicit", "unstick", "verify"]
    )
    await _warn_if_no_search_tools(workbench)
    out = capsys.readouterr().out
    assert "no search-capable tools" in out
    assert "UNVERIFIED" in out
    assert "Add a Splunk MCP server" in out
    # The warning lists what it did see, so the operator can judge the heuristic.
    assert "verify" in out


@pytest.mark.asyncio
async def test_no_warning_when_a_search_tool_exists(capsys) -> None:
    """A group with a real search server must not be flagged."""
    workbench = _FakeWorkbench(["splunk_search", "verify"])
    await _warn_if_no_search_tools(workbench)
    assert capsys.readouterr().out == ""


@pytest.mark.asyncio
async def test_marker_vocabulary_covers_the_documented_lookup_shapes() -> None:
    """Names containing these markers count as search-capable (pinned set)."""
    from peak_assistant.data_assistant import _warn_if_no_search_tools as _f  # noqa: F401

    # Pinned indirectly through the fake-workbench path to avoid reaching into
    # the function's private constant from more than one place.
    good_names = [
        "run_search", "saved_search", "query_events", "splunk_query",
        "index_lookup", "search_export", "eventkb_extract",
    ]
    workbench = _FakeWorkbench(good_names)

    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        await _warn_if_no_search_tools(workbench)
    assert buf.getvalue() == "", "a search-named tool was misclassified as non-search"


@pytest.mark.asyncio
async def test_empty_tool_list_also_warns(capsys) -> None:
    """A connected server exposing zero tools is the degenerate no-search case."""
    await _warn_if_no_search_tools(_FakeWorkbench([]))
    out = capsys.readouterr().out
    assert "no search-capable tools" in out
    assert "(none)" in out
