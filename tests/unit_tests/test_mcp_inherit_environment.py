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
"""Tests for the optional ``inheritEnvironment`` allowlist mode.

Follow-up to null-key env removal (env-merge design note): a server (or the
top-level config) may set ``inheritEnvironment: false`` to spawn stdio MCP
servers from an SDK-style minimal allowlist instead of the full parent
environment. Configured env values (strings and null removals) apply on top
in both modes.
"""

from __future__ import annotations

import json

import pytest

from peak_assistant.utils.mcp_config import (
    MINIMAL_INHERITED_ENV_KEYS,
    MCPConfigManager,
    resolve_server_env,
)


PARENT_ENV = {
    "PATH": "/usr/bin:/bin",
    "PATHEXT": ".COM;.EXE",
    "SYSTEMROOT": "C:\\WINDOWS",
    "TEMP": "C:\\Temp",
    "SECRET_TOKEN": "credential",
    "VOYAGE_API_KEY": "leak-me",
    "BRAVE_API_KEY": "also-mine",
}


def test_minimal_mode_starts_from_allowlist() -> None:
    result = resolve_server_env(PARENT_ENV, None, inherit_environment=False)
    assert set(result) == {"PATH", "PATHEXT", "SYSTEMROOT", "TEMP"}
    assert "SECRET_TOKEN" not in result
    assert "VOYAGE_API_KEY" not in result


def test_minimal_mode_still_applies_configured_values() -> None:
    result = resolve_server_env(
        PARENT_ENV,
        {"PARALLAX_BACKEND": "openai_compat"},
        inherit_environment=False,
    )
    assert result["PARALLAX_BACKEND"] == "openai_compat"
    assert "SECRET_TOKEN" not in result


def test_minimal_mode_combines_with_null_removal() -> None:
    """Null removal works in minimal mode too (defensive: key not inherited)."""
    result = resolve_server_env(
        PARENT_ENV,
        {"VOYAGE_API_KEY": None, "NEW_KEY": "v"},
        inherit_environment=False,
    )
    assert "VOYAGE_API_KEY" not in result
    assert result["NEW_KEY"] == "v"


def test_full_mode_is_the_default() -> None:
    result = resolve_server_env(PARENT_ENV, None)
    assert result["SECRET_TOKEN"] == "credential"
    assert result["VOYAGE_API_KEY"] == "leak-me"


def test_none_inherit_falls_back_to_global_default() -> None:
    explicit = resolve_server_env(
        PARENT_ENV, None, None, default_inherit_environment=False
    )
    assert set(explicit) == {"PATH", "PATHEXT", "SYSTEMROOT", "TEMP"}
    inherited = resolve_server_env(
        PARENT_ENV, None, None, default_inherit_environment=True
    )
    assert "SECRET_TOKEN" in inherited


def test_per_server_false_overrides_global_true() -> None:
    result = resolve_server_env(
        PARENT_ENV, None, inherit_environment=False, default_inherit_environment=True
    )
    assert "SECRET_TOKEN" not in result


def test_minimal_allowlist_covers_expected_keys() -> None:
    expected = {"PATH", "PATHEXT", "COMSPEC", "SYSTEMROOT", "WINDIR",
                "SYSTEMDRIVE", "TEMP", "TMP"}
    assert expected.issubset(set(MINIMAL_INHERITED_ENV_KEYS))


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary mcp_servers.json."""
    def _create(config_dict):
        path = tmp_path / "mcp_servers.json"
        path.write_text(json.dumps(config_dict), encoding="utf-8")
        return path
    return _create


def test_loader_parses_per_server_flag(config_file) -> None:
    path = config_file({
        "mcpServers": {
            "strict": {
                "command": "python",
                "args": ["-m", "server"],
                "inheritEnvironment": False,
            },
            "loose": {"command": "python", "args": []},
        }
    })
    manager = MCPConfigManager(str(path))
    assert manager.get_server_config("strict").inherit_environment is False
    assert manager.get_server_config("loose").inherit_environment is None


def test_loader_parses_top_level_default(config_file) -> None:
    path = config_file({
        "inheritEnvironment": False,
        "mcpServers": {"a": {"command": "python"}},
    })
    manager = MCPConfigManager(str(path))
    assert manager.get_inherit_environment_default() is False


def test_loader_default_is_true_when_absent(config_file) -> None:
    path = config_file({"mcpServers": {"a": {"command": "python"}}})
    manager = MCPConfigManager(str(path))
    assert manager.get_inherit_environment_default() is True


@pytest.mark.parametrize("bad", ["yes", 1, None])
def test_loader_rejects_non_bool_per_server(config_file, bad) -> None:
    if bad is None:
        bad = "true"  # placeholder replaced below to avoid None (valid absent)
    path = config_file({
        "mcpServers": {"a": {"command": "python", "inheritEnvironment": bad}}
    })
    with pytest.raises(ValueError, match="inheritEnvironment"):
        MCPConfigManager(str(path))


def test_loader_rejects_non_bool_top_level(config_file) -> None:
    path = config_file({
        "inheritEnvironment": "false",
        "mcpServers": {"a": {"command": "python"}},
    })
    with pytest.raises(ValueError, match="inheritEnvironment"):
        MCPConfigManager(str(path))


def test_save_round_trips_flags(config_file, tmp_path) -> None:
    path = config_file({
        "inheritEnvironment": False,
        "mcpServers": {
            "strict": {
                "command": "python",
                "inheritEnvironment": False,
                "env": {"K": None},
            },
            "optin": {"command": "python", "inheritEnvironment": True},
        },
    })
    manager = MCPConfigManager(str(path))
    manager._save_config()

    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded["inheritEnvironment"] is False
    assert reloaded["mcpServers"]["strict"]["inheritEnvironment"] is False
    assert reloaded["mcpServers"]["optin"]["inheritEnvironment"] is True
    # The default (True) server omits the key entirely
    fresh = MCPConfigManager(str(path))
    assert fresh.get_server_config("strict").inherit_environment is False
    assert fresh.get_inherit_environment_default() is False


def test_mcp_status_reflects_top_level_default(capsys, config_file) -> None:
    """Regression: status must resolve the effective mode, not assume it.

    A per-server None inherits the top-level inheritEnvironment default;
    printing "full parent copy" for such a server when the top-level
    default is false misreports the spawn-time behavior.
    """
    from peak_assistant.mcp_status.__main__ import print_server_status

    # Top-level false, no per-server override -> effective mode is minimal.
    path = config_file({
        "inheritEnvironment": False,
        "mcpServers": {"a": {"command": "python"}},
    })
    manager = MCPConfigManager(str(path))
    cfg = manager.get_server_config("a")
    print_server_status(
        "a", cfg, verbose=True,
        default_inherit_environment=manager.get_inherit_environment_default(),
    )
    out = capsys.readouterr().out
    assert "minimal allowlist (inheritEnvironment=false)" in out
    assert "full parent copy" not in out

    # Per-server True overrides the top-level default -> full copy.
    path = config_file({
        "inheritEnvironment": False,
        "mcpServers": {"b": {"command": "python", "inheritEnvironment": True}},
    })
    manager = MCPConfigManager(str(path))
    cfg = manager.get_server_config("b")
    print_server_status(
        "b", cfg, verbose=True,
        default_inherit_environment=manager.get_inherit_environment_default(),
    )
    out = capsys.readouterr().out
    assert "full parent copy" in out

    # No config anywhere -> full copy (historical default) still reported.
    path = config_file({"mcpServers": {"c": {"command": "python"}}})
    manager = MCPConfigManager(str(path))
    cfg = manager.get_server_config("c")
    print_server_status(
        "c", cfg, verbose=True,
        default_inherit_environment=manager.get_inherit_environment_default(),
    )
    out = capsys.readouterr().out
    assert "full parent copy (default)" in out
