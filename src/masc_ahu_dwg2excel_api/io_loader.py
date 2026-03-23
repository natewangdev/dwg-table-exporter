from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import ezdxf
from ezdxf.addons import odafc


def find_cad_files(root_dir: Path, recursive: bool = False) -> Iterable[Path]:
    """Find CAD files (.dxf / .dwg) under the given directory."""
    for path in root_dir.rglob("*") if recursive else root_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".dxf", ".dwg"}:
            yield path


def load_doc(path: Path):
    """Load a CAD document by extension.

    - .dxf: read directly via ezdxf.readfile
    - .dwg: convert via ODA File Converter (ezdxf.addons.odafc.readfile)
    """
    suffix = path.suffix.lower()
    if suffix == ".dxf":
        return ezdxf.readfile(path)
    if suffix == ".dwg":
        _apply_odafc_env_override()
        if not odafc.is_installed():
            raise RuntimeError(
                "DWG file detected but ODA File Converter is not configured. "
                "Set unix_exec_path / win_exec_path in ezdxf.ini [odafc-addon], "
                "or set the ODAFC_EXEC_PATH environment variable."
            )
        return odafc.readfile(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _apply_odafc_env_override() -> None:
    """Override the ODA executable path from the environment variable."""
    exec_path = os.getenv("ODAFC_EXEC_PATH", "").strip()
    if not exec_path:
        return
    if os.name == "nt":
        odafc.win_exec_path = exec_path
    else:
        odafc.unix_exec_path = exec_path
