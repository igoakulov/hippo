"""Tests for graph validation: hard errors vs warnings."""

import unittest
from unittest.mock import patch, MagicMock

from hippo.graph import build_graph, VALID_PROGRESS_VALUES


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.mock_scan = patch("hippo.graph.builder.scan_topics_dir")

    def test_validation_cases(self):
        cases = [
            # (topic_yaml, expected_errors, expected_issues)
            # Errors
            ("---\nid: same-id\ntitle: A\n---\n# A\n", ["Duplicate topic id:"], []),
            ("---\ntitle: No ID\n---\n# No ID\n", ["Missing topic id"], []),
            (
                '---\nid: bad-yaml\ntitle: "unclosed\n---\n# Bad\n',
                ["Metadata frontmatter cannot be parsed"],
                [],
            ),
            # Warnings/Issues
            (
                "---\nid: topic-x\ntitle: X\nparent: root\nsources: []\n---\n# X\n",
                [],
                ["no_sources"],
            ),
            (
                "---\nid: orphan-topic\ntitle: Orphan\nparent:\nsources:\n---\n# Orphan\n",
                [],
                ["no_parent"],
            ),
            (
                "---\nid: child\ntitle: Child\nparent: nonexistent\nsources:\n---\n# Child\n",
                [],
                ["orphan_parent"],
            ),
            (
                "---\nid: empty-topic\ntitle: Empty\nparent:\nsources:\n---\n",
                [],
                ["empty_body"],
            ),
            (
                "---\nid: bad-progress\ntitle: Bad\nparent:\nprogress: invalid-value\nsources:\n---\n# Bad\n",
                [],
                ["unknown_progress"],
            ),
            (
                "# Title\n---\nid: topic-y\ntitle: Y\n---\n# Title\n",
                [],
                ["frontmatter_position"],
            ),
            # Valid
            (
                "---\nid: good-topic\ntitle: Good\nparent:\nsources:\n---\n# Good\nBody text.\n",
                [],
                [],
            ),
        ]

        for yaml_content, expected_error_prefixes, expected_issue_types in cases:
            with self.subTest(yaml=yaml_content[:50]):
                mock_path_a = MagicMock()
                mock_path_a.stem = "test-topic-a"
                mock_path_a.name = "test-topic-a.md"
                mock_path_a.read_text.return_value = yaml_content

                if (
                    expected_error_prefixes
                    and expected_error_prefixes[0] == "Duplicate topic id:"
                ):
                    mock_path_b = MagicMock()
                    mock_path_b.stem = "test-topic-b"
                    mock_path_b.name = "test-topic-b.md"
                    mock_path_b.read_text.return_value = yaml_content
                    mock_paths = [mock_path_a, mock_path_b]
                else:
                    mock_paths = [mock_path_a]

                with self.mock_scan as mock_scan:
                    mock_scan.return_value = mock_paths
                    result = build_graph()

                # Check errors
                for prefix in expected_error_prefixes:
                    matching = [
                        e
                        for e in result.validation_errors
                        if e.message.startswith(prefix)
                    ]
                    self.assertGreater(
                        len(matching),
                        0,
                        f"Expected error starting with '{prefix}' for: {yaml_content[:50]}",
                    )

                # Check issues
                for issue_type in expected_issue_types:
                    matching = [
                        i for i in result.clean_issues if i.issue_type == issue_type
                    ]
                    self.assertGreater(
                        len(matching),
                        0,
                        f"Expected issue '{issue_type}' for: {yaml_content[:50]}",
                    )

    def test_valid_progress_values(self):
        self.assertEqual(VALID_PROGRESS_VALUES, {"new", "started", "completed"})

    def test_build_result_structure(self):
        mock_path = MagicMock()
        mock_path.stem = "good-topic"
        mock_path.name = "good-topic.md"
        mock_path.read_text.return_value = "---\nid: good-topic\ntitle: Good\nparent:\nsources:\n---\n# Good\nBody text.\n"

        with self.mock_scan as mock_scan:
            mock_scan.return_value = [mock_path]
            result = build_graph()

        self.assertIsInstance(result.validation_errors, list)
        self.assertIsInstance(result.clean_issues, list)
        self.assertTrue(hasattr(result, "topics"))
        self.assertTrue(hasattr(result, "clusters"))


if __name__ == "__main__":
    unittest.main()
