"""Install the bundled Patrycja mascot into Hermes' profile-local pet store."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

PLUGIN_VERSION = "1.0.0"
PET_SLUG = "patrycja"
SPRITESHEET_SHA256 = "e3f2e1bb04979926569b60cfa02471968fc52f966b27ce115c346da641ea9551"

_ROOT = Path(__file__).resolve().parent
_ASSETS = _ROOT / "assets"
_MARKER_NAME = ".patrycja-pet-plugin.json"
logger = logging.getLogger(__name__)


def _hermes_home() -> Path:
    """Resolve HERMES_HOME without depending on an internal Hermes module."""
    configured = os.environ.get("HERMES_HOME", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".hermes"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_copy(source: Path, destination: Path) -> None:
    temporary = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def install_pet() -> str:
    """Install or update Patrycja, preserving an unrelated same-slug pet."""
    source_sheet = _ASSETS / "spritesheet.webp"
    source_meta = _ASSETS / "pet.json"
    if _sha256(source_sheet) != SPRITESHEET_SHA256:
        raise RuntimeError("bundled Patrycja spritesheet failed its SHA-256 integrity check")

    destination = _hermes_home() / "pets" / PET_SLUG
    destination_sheet = destination / "spritesheet.webp"
    marker = destination / _MARKER_NAME

    destination.mkdir(parents=True, exist_ok=True)
    existing_matches = destination_sheet.is_file() and _sha256(destination_sheet) == SPRITESHEET_SHA256
    managed = marker.is_file()
    if destination_sheet.exists() and not managed and not existing_matches:
        logger.warning(
            "Patrycja pet was not installed: %s already contains an unrelated spritesheet",
            destination,
        )
        return "conflict"

    if not existing_matches:
        _atomic_copy(source_sheet, destination_sheet)
    _atomic_copy(source_meta, destination / "pet.json")

    marker_payload = {
        "plugin": "patrycja_pet",
        "version": PLUGIN_VERSION,
        "spritesheet_sha256": SPRITESHEET_SHA256,
    }
    marker.write_text(json.dumps(marker_payload, indent=2) + "\n", encoding="utf-8")
    logger.info("Patrycja mascot is installed at %s", destination)
    return "current" if existing_matches else "installed"


def _ensure_on_session_start(**_: Any) -> None:
    install_pet()


def register(ctx: Any) -> None:
    # Registration happens at gateway startup, so the pet appears before the
    # first session. The hook also self-heals a missing asset later on.
    install_pet()
    ctx.register_hook("on_session_start", _ensure_on_session_start)
