"""The approved contracts and all authored goldens stay frozen through build."""
import hashlib
import json
from pathlib import Path
import unittest


class RetainedSpecification(unittest.TestCase):
    def test_approved_contracts_and_declarative_assets_are_byte_identical(self):
        root=Path(__file__).resolve().parents[2]
        baseline=json.loads((root/'tests/support/spec_baseline.json').read_text())
        for name,expected in baseline.items():
            with self.subTest(name=name):self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),expected)
