"""Tests for graph validation: hard errors vs warnings."""

import unittest
from unittest.mock import patch, MagicMock

from hippo.graph_builder import (
    build_graph,
    VALID_PROGRESS_VALUES,
)


class TestValidationErrors(unittest.TestCase):
    def test_duplicate_topic_id_returns_validation_error(self):
        with patch("hippo.graph_builder.scan_topics_dir") as mock_scan:
            mock_path_a = MagicMock()
            mock_path_a.stem = "topic-a"
            mock_path_a.name = "topic-a.md"
            mock_path_a.read_text.return_value = (
                "---\nid: same-id\ntitle: A\n---\n# A\n"
            )
            mock_path_b = MagicMock()
            mock_path_b.stem = "topic-b"
            mock_path_b.name = "topic-b.md"
            mock_path_b.read_text.return_value = (
                "---\nid: same-id\ntitle: B\n---\n# B\n"
            )
            mock_scan.return_value = [mock_path_a, mock_path_b]

            result = build_graph()

            errors = [
                e
                for e in result.validation_errors
                if e.message.startswith("Duplicate topic id:")
            ]
            self.assertGreaterEqual(len(errors), 1)

    def test_missing_id_field_returns_validation_error(self):
        with patch("hippo.graph_builder.scan_topics_dir") as mock_scan:
            mock_path = MagicMock()
            mock_path.stem = "topic-x"
            mock_path.name = "topic-x.md"
            mock_path.read_text.return_value = "---\ntitle: No ID\n---\n# No ID\n"
            mock_scan.return_value = [mock_path]

            result = build_graph()

            self.assertEqual(len(result.validation_errors), 1)
            error = result.validation_errors[0]
            self.assertEqual(error.topic_id, "topic-x")
            self.assertEqual(error.filename, "topic-x.md")
            self.assertEqual(error.message, "Missing topic id")

    def test_unparseable_frontmatter_returns_validation_error(self):
        with patch("hippo.graph_builder.scan_topics_dir") as mock_scan:
            mock_path = MagicMock()
            mock_path.stem = "bad-yaml"
            mock_path.name = "bad-yaml.md"
            mock_path.read_text.return_value = (
                '---\nid: bad-yaml\ntitle: "unclosed\n---\n# Bad\n'
            )
            mock_scan.return_value = [mock_path]

            result = build_graph()

            errors = [
                e
                for e in result.validation_errors
                if e.message == "Metadata frontmatter cannot be parsed"
            ]
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].topic_id, "bad-yaml")
            self.assertEqual(errors[0].filename, "bad-yaml.md")

    def test_valid_progress_values_defined(self):
        self.assertEqual(VALID_PROGRESS_VALUES, {"new", "started", "completed"})


class TestValidationWarnings(unittest.TestCase):
    def test_no_sources_returns_clean_issue(self):
        with patch("hippo.graph_builder.scan_topics_dir") as mock_scan:
            mock_path = MagicMock()
            mock_path.stem = "topic-x"
            mock_path.name = "topic-x.md"
            mock_path.read_text.return_value = (
                "---\nid: topic-x\ntitle: X\nparent: root\nsources: []\n---\n# X\n"
            )
            mock_scan.return_value = [mock_path]

            result = build_graph()

            issues = [i for i in result.clean_issues if i.issue_type == "no_sources"]
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].topic_id, "topic-x")
            self.assertEqual(issues[0].filename, "topic-x.md")
            self.assertEqual(issues[0].message, "No sources")

    def test_no_parent_returns_clean_issue(self):
        with patch("hippo.graph_builder.scan_topics_dir") as mock_scan:
            mock_path = MagicMock()
            mock_path.stem = "orphan-topic"
            mock_path.name = "orphan-topic.md"
            mock_path.read_text.return_value = "---\nid: orphan-topic\ntitle: Orphan\nparent:\nsources:\n---\n# Orphan\n"
            mock_scan.return_value = [mock_path]

            result = build_graph()

            issues = [i for i in result.clean_issues if i.issue_type == "no_parent"]
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].topic_id, "orphan-topic")
            self.assertEqual(issues[0].filename, "orphan-topic.md")
            self.assertEqual(issues[0].message, "No parent")

    def test_orphan_parent_returns_clean_issue(self):
        with patch("hippo.graph_builder.scan_topics_dir") as mock_scan:
            mock_path = MagicMock()
            mock_path.stem = "child"
            mock_path.name = "child.md"
            mock_path.read_text.return_value = "---\nid: child\ntitle: Child\nparent: nonexistent\nsources:\n---\n# Child\n"
            mock_scan.return_value = [mock_path]

            result = build_graph()

            issues = [i for i in result.clean_issues if i.issue_type == "orphan_parent"]
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].topic_id, "child")
            self.assertEqual(issues[0].filename, "child.md")
            self.assertIn("nonexistent", issues[0].message)
            self.assertIn("Parent not found:", issues[0].message)

    def test_no_frontmatter_returns_issues(self):
        with patch("hippo.graph_builder.scan_topics_dir") as mock_scan:
            mock_path = MagicMock()
            mock_path.stem = "topic-y"
            mock_path.name = "topic-y.md"
            mock_path.read_text.return_value = (
                "# Title\n---\nid: topic-y\ntitle: Y\n---\n# Title\n"
            )
            mock_scan.return_value = [mock_path]

            result = build_graph()

            self.assertGreater(len(result.validation_errors), 0)
            self.assertGreater(len(result.clean_issues), 0)

    def test_empty_body_returns_clean_issue(self):
        with patch("hippo.graph_builder.scan_topics_dir") as mock_scan:
            mock_path = MagicMock()
            mock_path.stem = "empty-topic"
            mock_path.name = "empty-topic.md"
            mock_path.read_text.return_value = (
                "---\nid: empty-topic\ntitle: Empty\nparent:\nsources:\n---\n"
            )
            mock_scan.return_value = [mock_path]

            result = build_graph()

            issues = [i for i in result.clean_issues if i.issue_type == "empty_body"]
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].message, "Empty body")

    def test_unknown_progress_returns_clean_issue(self):
        with patch("hippo.graph_builder.scan_topics_dir") as mock_scan:
            mock_path = MagicMock()
            mock_path.stem = "bad-progress"
            mock_path.name = "bad-progress.md"
            mock_path.read_text.return_value = "---\nid: bad-progress\ntitle: Bad\nparent:\nprogress: invalid-value\nsources:\n---\n# Bad\n"
            mock_scan.return_value = [mock_path]

            result = build_graph()

            issues = [
                i for i in result.clean_issues if i.issue_type == "unknown_progress"
            ]
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].message, "Unknown progress: invalid-value")


class TestBuildResultStructure(unittest.TestCase):
    def test_build_result_has_validation_errors_and_clean_issues(self):
        with patch("hippo.graph_builder.scan_topics_dir") as mock_scan:
            mock_path = MagicMock()
            mock_path.stem = "good-topic"
            mock_path.name = "good-topic.md"
            mock_path.read_text.return_value = "---\nid: good-topic\ntitle: Good\nparent:\nsources:\n---\n# Good\nBody text.\n"
            mock_scan.return_value = [mock_path]

            result = build_graph()

            self.assertIsInstance(result.validation_errors, list)
            self.assertIsInstance(result.clean_issues, list)
            self.assertTrue(hasattr(result, "topics"))
            self.assertTrue(hasattr(result, "clusters"))


if __name__ == "__main__":
    unittest.main()
