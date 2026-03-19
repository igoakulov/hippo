"""Tests for diff computation: topic/connection changes, content word counts."""

import unittest
from hippo.diffs import Diff, compute_diff, _delta_str


class TestDeltaStr(unittest.TestCase):
    def test_positive_delta_prefixed_plus(self):
        self.assertEqual(_delta_str(10, 25), "+15")

    def test_negative_delta_plain(self):
        self.assertEqual(_delta_str(25, 10), "-15")

    def test_zero_delta_plain(self):
        self.assertEqual(_delta_str(5, 5), "0")


class TestComputeDiff(unittest.TestCase):
    def test_new_topic_marked_as_added(self):
        old = None
        new = {"topics": [{"id": "a", "title": "A", "parent": ""}]}

        diff = compute_diff(old, new)

        self.assertEqual(diff.topics_added[0]["id"], "a")
        self.assertEqual(diff.topics_deleted, [])

    def test_deleted_topic_marked_as_deleted(self):
        old = {"topics": [{"id": "a", "title": "A", "parent": ""}]}
        new = {"topics": []}

        diff = compute_diff(old, new)

        self.assertEqual(diff.topics_deleted, ["a"])
        self.assertEqual(diff.topics_added, [])

    def test_parent_change_recorded_as_metadata_change(self):
        old = {
            "topics": [{"id": "a", "title": "A", "parent": "root"}],
            "word_counts": {},
        }
        new = {
            "topics": [{"id": "a", "title": "A", "parent": "newparent"}],
            "word_counts": {"a": 0},
        }

        diff = compute_diff(old, new)

        self.assertIn("a", diff.topics_metadata_changed)
        self.assertEqual(diff.topics_metadata_changed["a"]["parent"]["old"], "root")
        self.assertEqual(
            diff.topics_metadata_changed["a"]["parent"]["new"], "newparent"
        )

    def test_parent_change_records_connection_deleted_and_added(self):
        old = {
            "topics": [{"id": "a", "title": "A", "parent": "root"}],
            "word_counts": {},
        }
        new = {
            "topics": [{"id": "a", "title": "A", "parent": "newparent"}],
            "word_counts": {"a": 0},
        }

        diff = compute_diff(old, new)

        added_conns = [
            (c["source"], c["target"], c["type"]) for c in diff.connections_added
        ]
        deleted_conns = [
            (c["source"], c["target"], c["type"]) for c in diff.connections_deleted
        ]
        self.assertIn(("a", "root", "parent"), deleted_conns)
        self.assertIn(("a", "newparent", "parent"), added_conns)

    def test_related_change_records_connections(self):
        old = {
            "topics": [{"id": "a", "title": "A", "related": ["x", "y"]}],
            "word_counts": {},
        }
        new = {
            "topics": [{"id": "a", "title": "A", "related": ["x", "z"]}],
            "word_counts": {"a": 0},
        }

        diff = compute_diff(old, new)

        added_conns = [
            (c["source"], c["target"], c["type"]) for c in diff.connections_added
        ]
        deleted_conns = [
            (c["source"], c["target"], c["type"]) for c in diff.connections_deleted
        ]
        self.assertIn(("a", "y", "related"), deleted_conns)
        self.assertIn(("a", "z", "related"), added_conns)

    def test_word_count_change_recorded(self):
        old = {"topics": [{"id": "a", "title": "A"}], "word_counts": {"a": 10}}
        new = {"topics": [{"id": "a", "title": "A"}], "word_counts": {"a": 30}}

        diff = compute_diff(old, new, {"a": 10})

        self.assertIn("a", diff.topics_content_changed)
        self.assertEqual(diff.topics_content_changed["a"]["old"], 10)
        self.assertEqual(diff.topics_content_changed["a"]["new"], 30)
        self.assertEqual(diff.topics_content_changed["a"]["delta"], "+20")

    def test_no_changes_returns_empty_diff(self):
        old = {
            "topics": [{"id": "a", "title": "A", "parent": ""}],
            "word_counts": {"a": 5},
        }
        new = {
            "topics": [{"id": "a", "title": "A", "parent": ""}],
            "word_counts": {"a": 5},
        }

        diff = compute_diff(old, new, {"a": 5})

        self.assertTrue(diff.is_empty())

    def test_cluster_change_recorded_as_metadata_change(self):
        old = {
            "topics": [{"id": "a", "title": "A", "cluster": "ml"}],
            "word_counts": {},
        }
        new = {
            "topics": [{"id": "a", "title": "A", "cluster": "nlp"}],
            "word_counts": {"a": 0},
        }

        diff = compute_diff(old, new)

        self.assertIn("a", diff.topics_metadata_changed)
        self.assertEqual(diff.topics_metadata_changed["a"]["cluster"]["old"], "ml")
        self.assertEqual(diff.topics_metadata_changed["a"]["cluster"]["new"], "nlp")


class TestDiffDataclass(unittest.TestCase):
    def test_is_empty_true_when_all_fields_empty(self):
        diff = Diff(timestamp="2026-03-19T10-00-00")
        self.assertTrue(diff.is_empty())

    def test_is_empty_false_when_topics_added(self):
        diff = Diff(timestamp="2026-03-19T10-00-00")
        diff.topics_added.append({"id": "a"})
        self.assertFalse(diff.is_empty())

    def test_to_dict_and_from_dict_roundtrip(self):
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
