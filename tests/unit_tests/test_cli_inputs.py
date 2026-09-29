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
"""Tests for the hybrid file-or-inline CLI content loader.

Divergence 3 from the integration research: ``-a``/``-c``/``-d`` style flags
now accept both an existing file path and inline content, while a path-shaped
value that does not exist still fails loudly (typing mistakes must not be
silently swallowed as inline text).
"""

from __future__ import annotations

import os
import tempfile

import pytest

from peak_assistant.utils.cli_inputs import load_cli_content


def _write_tmp(name: str, content: str) -> str:
    d = os.path.join(tempfile.gettempdir(), "peak-cli-inputs-test")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def test_existing_file_is_read() -> None:
    path = _write_tmp("content.md", "file body")
    assert load_cli_content(path, "ABLE information") == "file body"


def test_plain_text_is_inline_content() -> None:
    value = "The attacker used PowerShell for lateral movement."
    assert load_cli_content(value, "ABLE information") == value


def test_none_and_empty_return_none() -> None:
    assert load_cli_content(None, "Local context") is None
    assert load_cli_content("", "Local context") is None


@pytest.mark.parametrize(
    "value",
    [
        os.path.join("does", "not", "exist.md"),
        "missing-report.md",
        "C:\\no\\such\\dir\\notes.txt",
        "/no/such/dir/notes.txt",
    ],
)
def test_path_shaped_missing_value_is_hard_error(value: str) -> None:
    with pytest.raises(SystemExit) as excinfo:
        load_cli_content(value, "ABLE information")
    assert excinfo.value.code == 1


def test_missing_file_error_names_the_value(capsys) -> None:
    with pytest.raises(SystemExit):
        load_cli_content("no-such-report.md", "ABLE information")
    err = capsys.readouterr().err
    assert "no-such-report.md" in err
    assert "ABLE information" in err


def test_underspecified_extension_stays_path_shaped(tmp_path) -> None:
    # A value with a directory component never becomes inline content.
    value = str(tmp_path / "missing.md")
    with pytest.raises(SystemExit):
        load_cli_content(value, "Local context")


def test_content_containing_spl_like_text_round_trips() -> None:
    value = "index=winrm_hunt earliest=-24h | stats count by Computer"
    assert load_cli_content(value, "Local context") == value
