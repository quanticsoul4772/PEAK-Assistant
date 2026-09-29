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
"""Hybrid loading of CLI content flags (``-a``/``-c``/``-d``).

Divergence 3 from the integration research (``notes/m2-demo-evidence.md``):
the help text originally implied these flags take the content itself, but
every CLI treated the value as a file path. PR ``8b88d81`` aligned the help
text to "Path to ..."; this helper completes the fix in the other direction
by accepting both forms:

- a value that names an existing file is read from disk (unchanged behavior);
- a value that only *looks* like a path (path separators or a document
  extension) but does not exist fails loudly, exactly as before;
- anything else is treated as inline content.
"""

from __future__ import annotations

import os
import sys

# Extensions that mark a value as path-shaped even without a separator.
DOCUMENT_EXTENSIONS = frozenset({".md", ".txt", ".markdown", ".rst", ".log"})


def _looks_like_path(value: str) -> bool:
    if os.sep in value or "/" in value or "\\" in value:
        return True
    _, ext = os.path.splitext(value)
    return ext.lower() in DOCUMENT_EXTENSIONS


def load_cli_content(value: str | None, label: str) -> str | None:
    """Resolve a CLI content flag to text.

    Returns ``None`` when *value* is empty (the caller applies its own
    default), the file's content when *value* names an existing file, and
    *value* itself when it is not path-shaped. A path-shaped value that does
    not exist is a hard error (message on stderr, exit code 1), preserving
    the previous behavior for typo'd paths.

    *label* names the flag in error messages, e.g. ``"ABLE information"``.
    """
    if not value:
        return None

    if os.path.isfile(value):
        try:
            with open(value, "r", encoding="utf-8") as file:
                return file.read()
        except OSError as exc:
            print(f"Error reading {label}: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

    if _looks_like_path(value):
        print(f"Error: {label} file '{value}' not found", file=sys.stderr)
        raise SystemExit(1)

    return value
