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

"""Pins for ``mcp_servers.json.example`` (fork addition).

The example is the auto-copied starting config (``MCPConfigManager`` copies it
to ``mcp_servers.json`` when none exists), so it must stay valid and complete:
all required groups present, every referenced server defined, a genuinely
search-capable ``data_discovery`` group, and no literal secrets (secrets ride
``${VAR}`` interpolation).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "mcp_servers.json.example"


def test_example_exists_and_parses() -> None:
    assert EXAMPLE.exists(), "mcp_servers.json.example must ship in the repo root"
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert isinstance(data["mcpServers"], dict) and data["mcpServers"]
    assert isinstance(data["serverGroups"], dict) and data["serverGroups"]


def test_example_covers_all_required_groups() -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    groups = data["serverGroups"]
    for required in ("research-external", "local-data-search", "data_discovery"):
        assert required in groups, f"missing required group: {required}"
        assert groups[required], f"group must be non-empty: {required}"


def test_data_discovery_group_is_search_capable() -> None:
    """The group the discovery prompt points at Splunk through must contain a
    search-capable server — the failure mode where a group holds only
    corrective-memory tools triggered the UNVERIFIED warning (fork fix)."""
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    servers = data["mcpServers"]
    discovery = data["serverGroups"]["data_discovery"]
    assert discovery, "data_discovery group must not be empty"
    search_markers = ("search", "query", "splunk", "index", "savedsearch", "export", "event")
    for name in discovery:
        assert name in servers, f"group references undefined server: {name}"
    search_capable = any(
        any(marker in name.lower() for marker in search_markers) for name in discovery
    )
    assert search_capable, (
        f"data_discovery group {discovery} has no search-capable member; "
        "discovery would run ungrounded"
    )
    # The documented server is the Splunk MCP server (splunk/splunk-mcp-server2)
    # in stdio mode, with its connection env wired for interpolation.
    splunk = servers["splunk-mcp"]
    assert splunk["env"]["TRANSPORT"] == "stdio"
    assert "server.py" in " ".join(splunk["args"])


def test_every_group_member_is_a_defined_server() -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    servers = data["mcpServers"]
    for group, members in data["serverGroups"].items():
        for name in members:
            assert name in servers, f"group {group!r} references undefined server {name!r}"


def test_example_has_no_literal_secrets() -> None:
    raw = EXAMPLE.read_text(encoding="utf-8")
    for literal in ("tvly-dev-", "changeme", "YOUR-KEY", "YOUR-SPLUNK-AUTH-TOKEN"):
        assert literal not in raw, f"literal secret material in example: {literal}"
    placeholders = set(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)\}", raw))
    assert {"SPLUNK_HOST", "SPLUNK_TOKEN", "TAVILY_API_KEY"} <= placeholders, (
        f"expected env-interpolated placeholders, found: {sorted(placeholders)}"
    )


def test_example_key_scrub_blocks_env_merge_leak() -> None:
    """parallax's env block must neutralize the parent-shell key leak with
    empty strings (parallax normalizes blank to absent) — the divergence-1
    scrub pattern, now pinned in the shipped example."""
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    env = data["mcpServers"]["parallax"]["env"]
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "VOYAGE_API_KEY", "BRAVE_API_KEY"):
        assert env.get(key) == "", f"parallax env must scrub {key} to empty string"


def test_example_interpolates_cleanly_through_the_real_loader(monkeypatch, tmp_path) -> None:
    """Round-trip through MCPConfigManager's env interpolation the way the
    auto-copy path will consume it."""
    from peak_assistant.utils.mcp_config import MCPConfigManager

    monkeypatch.chdir(tmp_path)
    env = {
        "TAVILY_API_KEY": "test-tvly",
        "SPLUNK_HOST": "test-splunk",
        "SPLUNK_PORT": "8089",
        "SPLUNK_TOKEN": "test-token",
        "OPENAI_API_BASE": "http://localhost:11434/v1",
        "OPENAI_MODEL": "test-model",
        "PARALLAX_DATABASE_PATH": "test.db",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    mgr = MCPConfigManager.__new__(MCPConfigManager)
    data = mgr._interpolate_env(json.loads(EXAMPLE.read_text(encoding="utf-8")))
    assert data["mcpServers"]["splunk-mcp"]["env"]["SPLUNK_HOST"] == "test-splunk"
    assert data["serverGroups"]["data_discovery"] == ["splunk-mcp", "parallax"]
    leftovers = re.findall(r"\$\{[A-Z_][A-Z0-9_]*\}", json.dumps(data))
    assert not leftovers, f"unresolved placeholders after interpolation: {leftovers}"
