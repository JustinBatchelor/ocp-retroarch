import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("bundle", Path(__file__).resolve().parents[1] / "scripts/core-bundle.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class ArchiveSafety(unittest.TestCase):
    def archive(self, name):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr(name, b"test-core")
        return data.getvalue()

    def test_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                bundle.unpack(self.archive("../../escape.so"), Path(d), ".so")

    def test_rejects_absolute_path(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                bundle.unpack(self.archive("/tmp/escape.so"), Path(d), ".so")

    def test_extracts_and_records_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            files = bundle.unpack(self.archive("test_libretro.so"), Path(d), ".so")
            self.assertEqual(files[0]["sha256"], bundle.sha(b"test-core"))
            self.assertEqual((Path(d) / "test_libretro.so").read_bytes(), b"test-core")

    def test_rejects_corrupted_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder = root / "core-bundle"
            (folder / "archives").mkdir(parents=True)
            (folder / "archives/test.zip").write_bytes(b"modified")
            (root / "cores.lock.json").write_text(json.dumps({"bundle_id": "test", "archives": [
                {"name": "test.zip", "sha256": bundle.sha(b"original"), "kind": "core", "files": []}]}))
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                bundle.verify(root)
