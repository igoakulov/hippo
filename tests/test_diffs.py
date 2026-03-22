"""Tests for diff computation: topic/connection changes, content word counts."""

import unittest
from hippo.graph.diffs import Diff, compute_diff, _delta_str


class TestDiffs(unittest.TestCase):
    def test_delta_str_cases(self):
        cases = [
            (10, 25, "+15", "positive delta"),
            (25, 10, "-15", "negative delta"),
            (5, 5, "0", "zero delta"),
        ]
        for old, new, expected, desc in cases:
            self.assertEqual(_delta_str(old, new), expected, f"Failed: {desc}")

    def test_compute_diff_cases(self):
        cases = [
            # (old, new, description)
            (None, {"topics": [{"id": "a", "title": "A", "parent": ""}]}, "new topic"),
            (
                {"topics": [{"id": "a", "title": "A", "parent": ""}]},
                {"topics": []},
                "deleted topic",
            ),
            (
                {
                    "topics": [
                        {"id": "a", "title": "A", "parent": "root", "word_count": 0}
                    ]
                },
                {
                    "topics": [
                        {
                            "id": "a",
                            "title": "A",
                            "parent": "newparent",
                            "word_count": 0,
                        }
                    ]
                },
                "parent change",
            ),
            (
                {
                    "topics": [
                        {
                            "id": "a",
                            "title": "A",
                            "related": ["x", "y"],
                            "word_count": 0,
                        }
                    ]
                },
                {
                    "topics": [
                        {
                            "id": "a",
                            "title": "A",
                            "related": ["x", "z"],
                            "word_count": 0,
                        }
                    ]
                },
                "related change",
            ),
            (
                {"topics": [{"id": "a", "title": "A", "word_count": 10}]},
                {"topics": [{"id": "a", "title": "A", "word_count": 30}]},
                "word count change",
            ),
            (
                {"topics": [{"id": "a", "title": "A", "parent": "", "word_count": 5}]},
                {"topics": [{"id": "a", "title": "A", "parent": "", "word_count": 5}]},
                "no change",
            ),
            (
                {
                    "topics": [
                        {"id": "a", "title": "A", "cluster": "ml", "word_count": 0}
                    ]
                },
                {
                    "topics": [
                        {"id": "a", "title": "A", "cluster": "nlp", "word_count": 0}
                    ]
                },
                "cluster change",
            ),
        ]

        for old, new, desc in cases:
            with self.subTest(desc=desc):
                diff = compute_diff(old, new)

                if desc == "new topic":
                    self.assertEqual(diff.topics_added[0]["id"], "a")
                    self.assertEqual(diff.topics_deleted, [])
                elif desc == "deleted topic":
                    self.assertEqual(diff.topics_deleted, ["a"])
                    self.assertEqual(diff.topics_added, [])
                elif desc == "parent change":
                    self.assertIn("a", diff.topics_metadata_changed)
                    self.assertEqual(
                        diff.topics_metadata_changed["a"]["parent"]["old"], "root"
                    )
                    self.assertEqual(
                        diff.topics_metadata_changed["a"]["parent"]["new"], "newparent"
                    )
                    # Also check connections
                    added = [
                        (c["source"], c["target"], c["type"])
                        for c in diff.connections_added
                    ]
                    deleted = [
                        (c["source"], c["target"], c["type"])
                        for c in diff.connections_deleted
                    ]
                    self.assertIn(("a", "root", "parent"), deleted)
                    self.assertIn(("a", "newparent", "parent"), added)
                elif desc == "related change":
                    added = [
                        (c["source"], c["target"], c["type"])
                        for c in diff.connections_added
                    ]
                    deleted = [
                        (c["source"], c["target"], c["type"])
                        for c in diff.connections_deleted
                    ]
                    self.assertIn(("a", "y", "related"), deleted)
                    self.assertIn(("a", "z", "related"), added)
                elif desc == "word count change":
                    self.assertIn("a", diff.topics_content_changed)
                    self.assertEqual(diff.topics_content_changed["a"]["old"], 10)
                    self.assertEqual(diff.topics_content_changed["a"]["new"], 30)
                    self.assertEqual(diff.topics_content_changed["a"]["delta"], "+20")
                elif desc == "no change":
                    self.assertTrue(diff.is_empty())
                elif desc == "cluster change":
                    self.assertIn("a", diff.topics_metadata_changed)
                    self.assertEqual(
                        diff.topics_metadata_changed["a"]["cluster"]["old"], "ml"
                    )
                    self.assertEqual(
                        diff.topics_metadata_changed["a"]["cluster"]["new"], "nlp"
                    )

    def test_diff_dataclass(self):
        # is_empty tests
        diff = Diff(timestamp="2026-03-19T10-00-00")
        self.assertTrue(diff.is_empty())

        diff.topics_added.append({"id": "a"})
        self.assertFalse(diff.is_empty())

        # Roundtrip test
        diff = Diff(
            timestamp="2026-03-19T10-00-00",
            topics_added=[{"id": "a"}],
            connections_added=[{"source": "a", "target": "b", "type": "related"}],
        )
        serialized = diff.to_dict()
        restored = Diff.from_dict(serialized)
        self.assertEqual(restored.timestamp, "2026-03-19T10-00-00")
        self.assertEqual(len(restored.topics_added), 1)
        self.assertEqual(restored.topics_added[0]["id"], "a")


if __name__ == "__main__":
    unittest.main()
