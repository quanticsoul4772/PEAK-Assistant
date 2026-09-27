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

"""CLI help-text vs behavior parity tests.

Divergence 3 from the integration research (notes/m2-demo-evidence.md): the
``-a``/``-c`` (and planning's ``-d``) flags are documented as taking the
information/content itself, but every CLI actually treats the value as a
path to a file and reads it. These tests pin the aligned help text so the
mismatch cannot silently return.
"""

import importlib

import pytest

CASES = [
    ("peak_assistant.data_assistant.__main__", ["able_info", "local_context"]),
    ("peak_assistant.planning_assistant.__main__", ["able_info", "data_discovery", "local_context"]),
    ("peak_assistant.able_assistant.__main__", ["local_context"]),
    ("peak_assistant.hypothesis_assistant.hypothesis_refiner_cli", ["local_context"]),
]

PATH_PREFIXES = {
    "able_info": "Path to the ABLE information file",
    "data_discovery": "Path to the data discovery output file",
    "local_context": "Path to the local context file",
}


@pytest.mark.parametrize("module_name,flags", CASES)
def test_path_flags_are_documented_as_paths(module_name: str, flags: list) -> None:
    """Every file-backed flag's help text must say 'Path to ...'."""
    module = importlib.import_module(module_name)
    main = getattr(module, "main")
    source = main.__code__.co_consts
    strings = {c for c in source if isinstance(c, str)}
    for flag in flags:
        expected = PATH_PREFIXES[flag]
        assert any(s.startswith(expected) for s in strings), (
            f"{module_name}: --{flag} help text must start with {expected!r} "
            "(the CLI opens the value as a file path; the help text must say so)"
        )


@pytest.mark.parametrize("module_name,flags", CASES)
def test_content_wording_is_gone(module_name: str, flags: list) -> None:
    """The old content-implying help strings must not survive anywhere."""
    module = importlib.import_module(module_name)
    source = getattr(module, "main").__code__.co_consts
    strings = {c for c in source if isinstance(c, str)}
    for flag in flags:
        if flag == "able_info":
            stale = "The Actor, Behavior, Location and Evidence (ABLE) information"
        elif flag == "data_discovery":
            stale = "Data discovery information from previous agents"
        else:
            stale = "Additional local context to consider"
        assert not any(s == stale for s in strings), (
            f"{module_name}: stale content-implying help text for --{flag}: {stale!r}"
        )
