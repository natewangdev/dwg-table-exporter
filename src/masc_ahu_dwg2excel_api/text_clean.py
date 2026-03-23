from __future__ import annotations

import re

_MTEXT_FONT_PATTERN = re.compile(r"{\\f[^;]*;")
_MTEXT_CTRL_PATTERN = re.compile(r"\\[A-Za-z]+(?:[0-9.-]+)?")


def clean_cell_text(value: str) -> str:
    """Strip MTEXT formatting controls, keeping only readable text."""
    if not value:
        return ""

    text = str(value)

    # Normalise line breaks
    text = text.replace("\\P", "\n").replace("\\n", "\n")

    # Remove font-prefix sequences, e.g. {\fSimSun|b0|i0|c134|p2;
    text = _MTEXT_FONT_PATTERN.sub("", text)

    # Remove control sequences, e.g. \L \l \H1.0; etc.
    text = _MTEXT_CTRL_PATTERN.sub("", text)

    # Remove stray braces
    text = text.replace("{", "").replace("}", "")

    return text.strip()
