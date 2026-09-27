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

"""Tests that MCPConfigManager._save_config never persists secret values to disk."""

import json

from peak_assistant.utils.mcp_config import MCPConfigManager


SECRET_TOKEN = "SECRET_TOKEN_VALUE_XYZ"
SECRET_API_KEY = "SECRET_API_KEY_VALUE_XYZ"
SECRET_CLIENT_SECRET = "SECRET_CLIENT_SECRET_VALUE_XYZ"


def _make_config_file(tmp_path, monkeypatch):
    """Write a config with secret and non-secret auth fields; return its path."""
    # Make sure interpolation of any ${VAR} elsewhere in the test env cannot
    # interfere; the literals below need no interpolation.
    config = {
        "mcpServers": {
            "srv": {
                "transport": "stdio",
                "command": "echo",
                "auth": {
                    "type": "bearer",
                    "token": SECRET_TOKEN,
                    "api_key": SECRET_API_KEY,
                    "client_secret": SECRET_CLIENT_SECRET,
                    "client_id": "public-client-id",
                    "header_name": "X-Api-Key",
                },
            }
        },
        "serverGroups": {},
    }
    config_file = tmp_path / "mcp_servers.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")
    return str(config_file)


def test_save_config_never_persists_secret_auth_fields(tmp_path, monkeypatch):
    """Secret auth fields must not be written back to the config file."""
    config_file = _make_config_file(tmp_path, monkeypatch)
    manager = MCPConfigManager(config_file)

    manager._save_config()

    saved_text = open(config_file, encoding="utf-8").read()
    assert SECRET_TOKEN not in saved_text
    assert SECRET_API_KEY not in saved_text
    assert SECRET_CLIENT_SECRET not in saved_text

    # Non-secret auth metadata is still persisted.
    saved = json.loads(saved_text)
    auth = saved["mcpServers"]["srv"]["auth"]
    assert auth["client_id"] == "public-client-id"
    assert auth["header_name"] == "X-Api-Key"
    assert "token" not in auth
    assert "api_key" not in auth
    assert "client_secret" not in auth
