"""Regression checks for isolated replay safety and comparison boundaries."""

from pathlib import Path
import tempfile
import unittest

from reproduce_isolated import comparison, contained_file, create_workspace


class IsolatedReplayTests(unittest.TestCase):
    """Exercise path safety and keep scientific differences visible."""

    def test_runtime_metadata_is_only_exclusion(self):
        """A different interpreter does not alter the scientific comparison."""
        self.assertEqual(comparison({'environment': 1, 'records': [1]},
                                    {'environment': 2, 'records': [1]}), [])

    def test_scientific_change_is_rejected(self):
        """Changed results or absent scientific fields cannot pass."""
        self.assertEqual(comparison({'records': [1]}, {'records': [2]}), ['records'])
        self.assertEqual(comparison({'seed': None}, {}), ['seed'])

    def test_existing_destination_is_rejected(self):
        """Even an empty preexisting destination is never reused."""
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / 'source'
            source.mkdir()
            with self.assertRaises(ValueError):
                create_workspace(source, base)

    def test_project_child_is_rejected(self):
        """A replay cannot write inside its original project."""
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                create_workspace(Path(root), Path(root) / 'replay')

    def test_missing_and_traversal_inputs_are_rejected(self):
        """Missing input and outside paths fail before copying."""
        with tempfile.TemporaryDirectory() as root:
            for relative in ('missing.json', '../outside.json'):
                with self.assertRaises(ValueError):
                    contained_file(Path(root), relative)


if __name__ == '__main__':
    unittest.main()
