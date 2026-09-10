from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("patrycja_pet", ROOT / "__init__.py")
PLUGIN = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PLUGIN)


class InstallerTests(unittest.TestCase):
    def test_installs_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {"HERMES_HOME": temporary}):
            self.assertEqual(PLUGIN.install_pet(), "installed")
            self.assertEqual(PLUGIN.install_pet(), "current")

            pet_dir = Path(temporary) / "pets" / "patrycja"
            metadata = json.loads((pet_dir / "pet.json").read_text(encoding="utf-8"))
            digest = hashlib.sha256((pet_dir / "spritesheet.webp").read_bytes()).hexdigest()
            self.assertEqual(metadata["id"], "patrycja")
            self.assertEqual(digest, PLUGIN.SPRITESHEET_SHA256)

    def test_preserves_unmanaged_same_slug_pet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {"HERMES_HOME": temporary}):
            pet_dir = Path(temporary) / "pets" / "patrycja"
            pet_dir.mkdir(parents=True)
            existing = b"somebody else's mascot"
            (pet_dir / "spritesheet.webp").write_bytes(existing)

            self.assertEqual(PLUGIN.install_pet(), "conflict")
            self.assertEqual((pet_dir / "spritesheet.webp").read_bytes(), existing)


if __name__ == "__main__":
    unittest.main()

