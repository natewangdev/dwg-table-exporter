from __future__ import annotations

import re

_MTEXT_FONT_PATTERN = re.compile(r"{\\f[^;]*;")
_MTEXT_CTRL_PATTERN = re.compile(r"\\[A-Za-z]+(?:[0-9.-]+)?")


def clean_cell_text(value: str) -> str:
    """去掉 MTEXT 格式控制，只保留可读文本."""
    if not value:
        return ""

    text = str(value)

    # 处理换行符
    text = text.replace("\\P", "\n").replace("\\n", "\n")

    # 去掉字体格式前缀，如 {\fSimSun|b0|i0|c134|p2;
    text = _MTEXT_FONT_PATTERN.sub("", text)

    # 去掉控制序列，如 \L \l \H1.0; 等
    text = _MTEXT_CTRL_PATTERN.sub("", text)

    # 去掉多余的大括号
    text = text.replace("{", "").replace("}", "")

    return text.strip()

