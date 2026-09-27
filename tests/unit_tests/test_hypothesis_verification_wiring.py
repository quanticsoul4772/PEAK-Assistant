# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# SPDX-License-Identifier: MIT

"""Opt-in hypothesis-verification wiring tests (roadmap M4).

Mocked only — no MCP server, model client, or network is involved. These tests
pin the compatibility-table guarantees from the finalized integration memo:
the default path constructs agents exactly as before with no MCP activity,
and the verification group surfaces exactly the allow-listed tools.
"""

import sys
from typing import Any, Dict, List, Mapping, Optional

import pytest
from autogen_core import CancellationToken
from autogen_core.tools import TextResultContent, ToolResult, ToolSchema, Workbench

from peak_assistant.hypothesis_assistant import hypothesis_refiner_cli as cli
from peak_assistant.hypothesis_assistant.hypothesis_refiner_cli import (
    _AllowlistWorkbench,
    _resolve_verification_workbench,
)


class _StubWorkbench(Workbench):
    """Minimal in-memory workbench: four tools, records every call."""

    def __init__(self) -> None:
        self.started = False
        self.calls: List[str] = []

    async def list_tools(self) -> List[ToolSchema]:
        names = ["grounded_verify", "surface", "unstick", "verify"]
        return [
            ToolSchema(
                name=name,
                description=f"{name} stub",
                parameters={"type": "object", "properties": {}},
            )
            for name in names
        ]

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        cancellation_token: CancellationToken | None = None,
        call_id: str | None = None,
    ) -> ToolResult:
        self.calls.append(name)
        return ToolResult(name=name, is_error=False, result=[TextResultContent(content=f"{name} ok")])

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.started = False

    async def reset(self) -> None:
        self.calls.clear()

    async def save_state(self) -> Mapping[str, Any]:
        return {"calls": list(self.calls)}

    async def load_state(self, state: Mapping[str, Any]) -> None:
        self.calls = list(state.get("calls", []))


class _StopTeam(Exception):
    """Raised by the team stub to stop refiner() right after agent construction."""


class _TeamStub:
    """RoundRobinGroupChat stand-in that records participants, then stops."""

    def __init__(self, participants: Any, **kwargs: Any) -> None:
        raise _StopTeam(str([type(p).__name__ for p in participants]))


@pytest.fixture()
def captured_agents(
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    """Patch AssistantAgent (spy), model clients (stubs) and the team (sentinel)."""

    class Capture:
        agents: List[Dict[str, Any]] = []

    async def _stub_client(agent_name: Optional[str] = None) -> object:
        return object()

    def _spy_agent(*args: Any, **kwargs: Any) -> object:
        Capture.agents.append(dict(kwargs))
        return object()

    monkeypatch.setattr(cli, "get_model_client", _stub_client)
    monkeypatch.setattr(cli, "AssistantAgent", _spy_agent)
    monkeypatch.setattr(cli, "RoundRobinGroupChat", _TeamStub)
    return Capture


def _refiner_inputs() -> Dict[str, Any]:
    return {
        "hypothesis": "The attacker used PowerShell for lateral movement.",
        "local_context": "ctx",
        "research_document": "research",
        "local_data_document": "data",
    }


def _critic_kwargs(captured: Any) -> Dict[str, Any]:
    matches = [
        kw
        for kw in captured.agents
        if kw.get("system_message", "").lstrip().startswith("You are an expert")
    ]
    assert len(matches) == 1, f"expected exactly one critic construction, got {len(matches)}"
    return matches[0]


def _refiner_kwargs(captured: Any) -> Dict[str, Any]:
    matches = [
        kw
        for kw in captured.agents
        if kw.get("system_message", "").lstrip().startswith("You are a threat hunting")
    ]
    assert len(matches) == 1, f"expected exactly one refiner construction, got {len(matches)}"
    return matches[0]


async def test_t1_default_path_constructs_critic_without_workbench(
    captured_agents: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default parity: group=None constructs agents as before, no MCP activity."""
    resolver_calls = {"n": 0}

    async def _counting_resolver(group: str, verbose: bool = False) -> Optional[Workbench]:
        resolver_calls["n"] += 1
        return None

    monkeypatch.setattr(cli, "_resolve_verification_workbench", _counting_resolver)

    with pytest.raises(_StopTeam):
        await cli.refiner(**_refiner_inputs(), mcp_server_group=None)

    assert len(captured_agents.agents) == 2
    critic_kwargs = _critic_kwargs(captured_agents)
    assert "workbench" not in critic_kwargs
    assert "reflect_on_tool_use" not in critic_kwargs
    assert "model_client" in critic_kwargs
    assert resolver_calls["n"] == 0


async def test_t2_allowlist_filters_list_tools() -> None:
    """list_tools surfaces exactly grounded_verify and verify, schemas preserved."""
    stub = _StubWorkbench()
    wrapped = _AllowlistWorkbench(stub)

    tools = await wrapped.list_tools()

    assert [tool["name"] for tool in tools] == ["grounded_verify", "verify"]
    for tool in tools:
        assert tool["description"] == f"{tool['name']} stub"
        assert tool["parameters"] == {"type": "object", "properties": {}}


async def test_t3_allowlist_enforces_call_tool() -> None:
    """Disallowed tool calls raise; allowed calls and lifecycle delegate."""
    stub = _StubWorkbench()
    wrapped = _AllowlistWorkbench(stub)

    with pytest.raises(ValueError, match="not allowed"):
        await wrapped.call_tool("surface", {"prompt": "recall memories"})

    result = await wrapped.call_tool("verify", {"claim": "hyp-1"})
    assert result.is_error is False
    assert result.result[0].content == "verify ok"
    assert stub.calls == ["verify"]

    await wrapped.start()
    assert stub.started is True
    state = await wrapped.save_state()
    assert state == {"calls": ["verify"]}
    await wrapped.load_state({"calls": []})
    await wrapped.reset()
    assert stub.calls == []


async def test_t4_resolution_is_never_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    """An absent group resolves to None instead of raising."""

    async def _connect(group: str, user_id: Optional[str] = None) -> List[str]:
        return []

    # The resolver imports mcp_config lazily, so patch at the source module.
    monkeypatch.setattr("peak_assistant.utils.mcp_config.setup_mcp_servers", _connect)

    resolved = await _resolve_verification_workbench("hypothesis-verification")
    assert resolved is None


async def test_t4b_resolution_wraps_connected_workbench(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A connected group yields the allow-listed workbench for the first server."""

    class _Manager:
        def get_workbench(self, server_name: str) -> Optional[Workbench]:
            return _StubWorkbench() if server_name == "parallax" else None

    async def _connect(group: str, user_id: Optional[str] = None) -> List[str]:
        assert group == "hypothesis-verification"
        return ["parallax"]

    monkeypatch.setattr("peak_assistant.utils.mcp_config.setup_mcp_servers", _connect)
    monkeypatch.setattr("peak_assistant.utils.mcp_config.get_client_manager", lambda: _Manager())

    resolved = await _resolve_verification_workbench("hypothesis-verification")

    assert isinstance(resolved, _AllowlistWorkbench)
    names = [tool["name"] for tool in await resolved.list_tools()]
    assert names == ["grounded_verify", "verify"]


async def test_t5_opt_in_wires_filtered_workbench_into_critic(
    captured_agents: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Opt-in path: the critic receives the allow-listed workbench; refiner does not."""

    async def _resolve(group: str, verbose: bool = False) -> Workbench:
        return _AllowlistWorkbench(_StubWorkbench())

    monkeypatch.setattr(cli, "_resolve_verification_workbench", _resolve)

    with pytest.raises(_StopTeam):
        await cli.refiner(**_refiner_inputs(), mcp_server_group="hypothesis-verification")

    assert len(captured_agents.agents) == 2
    critic_kwargs = _critic_kwargs(captured_agents)
    assert isinstance(critic_kwargs["workbench"], _AllowlistWorkbench)
    assert critic_kwargs["reflect_on_tool_use"] is True
    refiner_kwargs = _refiner_kwargs(captured_agents)
    assert "workbench" not in refiner_kwargs
    assert "reflect_on_tool_use" not in refiner_kwargs


def test_t6_cli_flag_threads_through(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """--verification-group is parsed and reaches refiner(); default run omits it."""
    research = tmp_path / "research.md"
    research.write_text("research document", encoding="utf-8")

    seen_groups: List[Optional[str]] = []

    def _recording_refiner(**kwargs: Any) -> Any:
        seen_groups.append(kwargs.get("mcp_server_group"))
        raise RuntimeError("stop before any model call")

    monkeypatch.setattr(cli, "refiner", _recording_refiner)
    monkeypatch.setattr(cli, "find_dotenv_file", lambda: None)

    base = ["hypothesis_refiner_cli.py", "-y", "hyp", "-r", str(research), "--no-feedback"]
    for extra, expected in (
        ([], None),
        (["--verification-group", "hypothesis-verification"], "hypothesis-verification"),
    ):
        seen_groups.clear()
        monkeypatch.setattr(sys, "argv", base + extra)
        # main() catches the sentinel error and exits 1.
        with pytest.raises(SystemExit) as excinfo:
            cli.main()
        assert excinfo.value.code == 1
        assert seen_groups == [expected]
