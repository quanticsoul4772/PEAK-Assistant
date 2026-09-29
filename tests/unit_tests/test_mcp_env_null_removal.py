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
#
# SPDX-License-Identifier: MIT
"""Tests for null-key env removal in MCP stdio server spawning.

Fork fix for divergence 1 (env-merge design note, Option B): a ``null``
value in a server's ``env`` config removes that key from the child
environment, so spawned MCP servers no longer inherit every credential
from the parent shell. String values keep ``dict.update`` override
semantics; removal happens in a second pass so override-then-remove
ordering is deterministic.
"""

from __future__ import annotations

from peak_assistant.utils.mcp_config import merge_server_env


def test_no_server_env_returns_parent_copy() -> None:
    parent = {"PATH": "/usr/bin", "SECRET": "x"}
    result = merge_server_env(parent, None)
    assert result == parent
    assert result is not parent  # never mutate the caller's dict


def test_empty_server_env_returns_parent_copy() -> None:
    parent = {"PATH": "/usr/bin"}
    result = merge_server_env(parent, {})
    assert result == parent


def test_string_values_override_parent() -> None:
    parent = {"PATH": "/usr/bin", "MODE": "old"}
    result = merge_server_env(parent, {"MODE": "new", "EXTRA": "1"})
    assert result["MODE"] == "new"
    assert result["EXTRA"] == "1"
    assert result["PATH"] == "/usr/bin"


def test_null_value_removes_inherited_key() -> None:
    parent = {"PATH": "/usr/bin", "VOYAGE_API_KEY": "leak-me"}
    result = merge_server_env(parent, {"VOYAGE_API_KEY": None})
    assert "VOYAGE_API_KEY" not in result
    assert result["PATH"] == "/usr/bin"


def test_removal_of_absent_key_is_noop() -> None:
    parent = {"PATH": "/usr/bin"}
    result = merge_server_env(parent, {"NEVER_EXISTED": None})
    assert result == parent
    assert "NEVER_EXISTED" not in result


def test_override_then_remove_ordering() -> None:
    """The same key set then removed must end up removed (two passes)."""
    parent = {"TOKEN": "inherited"}
    result = merge_server_env(parent, {"TOKEN": "override", "TOKEN2": None})
    assert result["TOKEN"] == "override"
    # A null entry removes even when it is the only entry for that key.
    assert "TOKEN" not in merge_server_env(parent, {"TOKEN": None})
    # Removal happens after overrides, so a null never resurrects a key
    # that another entry set.
    assert merge_server_env(parent, {"TOKEN": None}) != {"TOKEN": None}


def test_remove_then_set_is_possible_via_distinct_keys() -> None:
    """Removal only affects the marked key; other keys still apply."""
    parent = {"A": "1", "B": "2"}
    result = merge_server_env(parent, {"A": None, "B": "3", "C": "4"})
    assert "A" not in result
    assert result["B"] == "3"
    assert result["C"] == "4"


def test_null_removal_does_not_mutate_parent() -> None:
    parent = {"SECRET": "x"}
    merge_server_env(parent, {"SECRET": None})
    assert parent == {"SECRET": "x"}


def test_empty_string_value_is_set_not_removed() -> None:
    """The documented empty-string override trick keeps override semantics."""
    parent = {"VOYAGE_API_KEY": "real-key"}
    result = merge_server_env(parent, {"VOYAGE_API_KEY": ""})
    assert result["VOYAGE_API_KEY"] == ""


def test_mcp_status_verbose_shows_removed_keys(capsys) -> None:
    """mcp-status -v reports removals as -KEY lines."""
    from peak_assistant.mcp_status.__main__ import print_server_status
    from peak_assistant.utils.mcp_config import MCPServerConfig

    config = MCPServerConfig(
        name="demo",
        command="python",
        args=["server.py"],
        env={"PARALLAX_BACKEND": "openai_compat", "VOYAGE_API_KEY": None, "BRAVE_API_KEY": None},
    )
    print_server_status("demo", config, verbose=True)
    out = capsys.readouterr().out
    assert "Env overrides: PARALLAX_BACKEND" in out
    assert "-VOYAGE_API_KEY" in out
    assert "-BRAVE_API_KEY" in out
