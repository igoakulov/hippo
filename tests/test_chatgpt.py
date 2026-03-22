import unittest
import tempfile
import json
import os
from pathlib import Path


class TestContentTypes(unittest.TestCase):
    def setUp(self):
        from hippo.parsers.chatgpt import (
            INCLUDE_CONTENT_TYPES,
            EXCLUDE_CONTENT_TYPES,
            should_include_message,
        )

        self.INCLUDE_CONTENT_TYPES = INCLUDE_CONTENT_TYPES
        self.EXCLUDE_CONTENT_TYPES = EXCLUDE_CONTENT_TYPES
        self.should_include_message = should_include_message

    def test_included_content_types(self):
        self.assertIn("text", self.INCLUDE_CONTENT_TYPES)
        self.assertIn("execution_output", self.INCLUDE_CONTENT_TYPES)
        self.assertNotIn("code", self.INCLUDE_CONTENT_TYPES)

    def test_excluded_content_types(self):
        self.assertIn("user_editable_context", self.EXCLUDE_CONTENT_TYPES)
        self.assertIn("thoughts", self.EXCLUDE_CONTENT_TYPES)
        self.assertIn("reasoning_recap", self.EXCLUDE_CONTENT_TYPES)

    def test_message_inclusion_rules(self):
        cases = [
            # (should_include, msg_dict)
            (
                True,
                {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["hello"]},
                    "metadata": {},
                },
            ),
            (
                True,
                {
                    "author": {"role": "assistant"},
                    "content": {"content_type": "text", "parts": ["response"]},
                    "metadata": {},
                },
            ),
            (
                False,
                {
                    "author": {"role": "system"},
                    "content": {"content_type": "text", "parts": ["system"]},
                    "metadata": {},
                },
            ),
            (
                False,
                {
                    "author": {"role": "tool", "name": "web"},
                    "content": {"content_type": "text", "parts": ["tool"]},
                    "metadata": {},
                },
            ),
            (
                False,
                {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["hidden"]},
                    "metadata": {"is_visually_hidden_from_conversation": True},
                },
            ),
            (
                False,
                {
                    "author": {"role": "user"},
                    "content": {
                        "content_type": "user_editable_context",
                        "parts": ["profile"],
                    },
                    "metadata": {},
                },
            ),
            (
                False,
                {
                    "author": {"role": "assistant"},
                    "content": {"content_type": "text", "parts": [""]},
                    "metadata": {},
                },
            ),
            (
                False,
                {
                    "author": {"role": "assistant"},
                    "content": {"content_type": "code", "text": "{}"},
                    "metadata": {},
                },
            ),
        ]
        for expected, msg in cases:
            self.assertEqual(
                self.should_include_message(msg),
                expected,
                f"Failed for msg: {msg.get('author', {}).get('role')}/{msg.get('content', {}).get('content_type')}",
            )


class TestFilters(unittest.TestCase):
    def setUp(self):
        from hippo.parsers.chatgpt import filter_conversations

        self.filter_conversations = filter_conversations
        self.convs = [
            {
                "conversation_id": "1",
                "title": "Test Conversation A",
                "create_time": 1700000000.0,
                "mapping": {},
            },
            {
                "conversation_id": "2",
                "title": "Test Conversation B",
                "create_time": 1700100000.0,
                "mapping": {},
            },
            {
                "conversation_id": "3",
                "title": "Other Conversation",
                "create_time": 1700200000.0,
                "mapping": {},
            },
        ]

    def test_filter_cases(self):
        cases = [
            # (expected_count, from_time, till_time, titles, description)
            (3, None, None, None, "no filters"),
            (2, None, None, ["Test"], "single title"),
            (2, None, None, ["Conversation A", "Conversation B"], "multiple titles"),
            (2, 1700100000.0, None, None, "from_time"),
            (2, None, 1700100000.0, None, "till_time"),
            (1, 1700100000.0, 1700100000.0, None, "time range"),
            (1, 1700000000.0, 1700050000.0, ["Test"], "combined filters"),
        ]
        for expected, from_t, till_t, titles, desc in cases:
            result = self.filter_conversations(self.convs, from_t, till_t, titles)
            self.assertEqual(len(result), expected, f"Failed for: {desc}")


class TestExpand(unittest.TestCase):
    def setUp(self):
        from hippo.parsers.chatgpt import (
            parse_conversation_expand,
            Conversation,
            get_last_message_id,
        )

        self.parse_conversation_expand = parse_conversation_expand
        self.get_last_message_id = get_last_message_id
        self.Conversation = Conversation
        base_mapping = {
            "root": {
                "id": "root",
                "parent": None,
                "children": ["msg1", "msg2", "msg3"],
            },
            "msg1": {
                "id": "msg1",
                "parent": "root",
                "children": [],
                "message": {
                    "id": "msg1",
                    "author": {"role": "user"},
                    "create_time": 1700000001.0,
                    "content": {"content_type": "text", "parts": ["first"]},
                    "metadata": {},
                },
            },
            "msg2": {
                "id": "msg2",
                "parent": "root",
                "children": [],
                "message": {
                    "id": "msg2",
                    "author": {"role": "assistant"},
                    "create_time": 1700000002.0,
                    "content": {"content_type": "text", "parts": ["second"]},
                    "metadata": {},
                },
            },
            "msg3": {
                "id": "msg3",
                "parent": "root",
                "children": [],
                "message": {
                    "id": "msg3",
                    "author": {"role": "user"},
                    "create_time": 1700000003.0,
                    "content": {"content_type": "text", "parts": ["third"]},
                    "metadata": {},
                },
            },
        }
        self.base_conv_data = {
            "conversation_id": "test123",
            "title": "Test",
            "create_time": 1700000000.0,
            "mapping": base_mapping,
        }

    def test_expand_cases(self):
        cases = [
            # (last_id, expected_msg_ids, description)
            (None, ["msg1", "msg2", "msg3"], "no filter - all messages"),
            ("msg1", ["msg2", "msg3"], "skip before last_id"),
            ("msg2", ["msg3"], "skip up to last_id"),
        ]
        for last_id, expected_ids, desc in cases:
            conv = self.parse_conversation_expand(self.base_conv_data, last_id)
            self.assertEqual(
                [m.id for m in conv.messages], expected_ids, f"Failed for: {desc}"
            )

        from hippo.parsers.chatgpt import get_output_filename

        conv = self.parse_conversation_expand(self.base_conv_data, None)
        old_filename = get_output_filename(conv)

        conv.title = "Renamed Conversation"
        new_filename = get_output_filename(conv)
        self.assertNotEqual(old_filename, new_filename)
        self.assertIn("renamed-conversation", new_filename)

    def test_last_message_id(self):
        cases = [
            # (messages, expected_id, description)
            (["msg1", "user", "Hello"], "msg1", "single message"),
            (
                [
                    "msg1",
                    "user",
                    "Hello",
                    "msg2",
                    "assistant",
                    "Hi",
                    "msg3",
                    "user",
                    "Bye",
                ],
                "msg3",
                "multiple messages",
            ),
            ([], "", "empty conversation"),
        ]
        for msg_args, expected_id, desc in cases:
            msgs = []
            for i in range(0, len(msg_args), 3):
                from hippo.parsers.chatgpt import MessageNode

                msgs.append(
                    MessageNode(
                        msg_args[i],
                        msg_args[i + 1],
                        msg_args[i + 2],
                        "2024-01-01",
                        "text",
                    )
                )
            conv = self.Conversation(
                id="test", title="Test", create_time=0, messages=msgs
            )
            self.assertEqual(
                self.get_last_message_id(conv), expected_id, f"Failed for: {desc}"
            )


class TestTransformations(unittest.TestCase):
    def setUp(self):
        from hippo.parsers.chatgpt import _build_cite_lookups, _transform_content

        self.build_cite_lookups = _build_cite_lookups
        self.transform = _transform_content

    def test_cite_lookups(self):
        msg = {
            "metadata": {
                "content_references": [
                    {
                        "type": "link_title",
                        "url": "https://example.com/",
                        "title": "Example Site",
                        "matched_text": "\ue200link_title\ue202Example Site\ue202key1\ue201",
                    },
                    {
                        "type": "grouped_webpages",
                        "url": "",
                        "items": [
                            {
                                "url": "https://example.com/page",
                                "title": "Page Title",
                                "attribution": "example.com",
                            }
                        ],
                        "matched_text": "\ue200cite\ue202key1\ue201",
                    },
                ]
            }
        }
        link_title_lookup, grouped_lookup = self.build_cite_lookups(msg)
        self.assertEqual(
            link_title_lookup["key1"], ("https://example.com/", "Example Site")
        )
        self.assertEqual(
            grouped_lookup["key1"], ("https://example.com/page", "example.com")
        )

    def test_content_transformations(self):
        cases = [
            # (input, msg, expected, description)
            (
                '\ue200genui\ue202{"math_block_widget_common_keywords":{"content":"a^2 + b^2 = c^2"}}\ue201',
                {},
                "\\(a^2 + b^2 = c^2\\)",
                "math block",
            ),
            (
                "\ue200filecite\ue202file123\ue201",
                {
                    "metadata": {
                        "content_references": [
                            {
                                "type": "file",
                                "name": "document.pdf",
                                "matched_text": "\ue200filecite\ue202file123\ue201",
                            }
                        ]
                    }
                },
                "[document.pdf]",
                "filecite",
            ),
            (
                '\ue200entity\ue202["app","ChatGPT"]\ue201',
                {},
                '["app","ChatGPT"]',
                "entity",
            ),
            (
                "\ue200link_title\ue202Open Site\ue202search1\ue201",
                {
                    "metadata": {
                        "content_references": [
                            {
                                "type": "link_title",
                                "url": "https://example.com/",
                                "title": "Open Site",
                                "matched_text": "\ue200link_title\ue202Open Site\ue202search1\ue201",
                            }
                        ],
                        "search_result_groups": [
                            {
                                "entries": [
                                    {
                                        "ref_id": {"turn_index": 0, "ref_index": 1},
                                        "url": "https://example.com/",
                                        "title": "Example",
                                    }
                                ]
                            }
                        ],
                    }
                },
                "[Open Site](https://example.com/)",
                "link_title",
            ),
            (
                "\ue200cite\ue202search1\ue201",
                {
                    "metadata": {
                        "content_references": [
                            {
                                "type": "grouped_webpages",
                                "url": "",
                                "items": [
                                    {
                                        "url": "https://ref.com/?utm_source=chatgpt.com",
                                        "attribution": "ref.com",
                                    }
                                ],
                                "matched_text": "\ue200cite\ue202search1\ue201",
                            }
                        ],
                        "search_result_groups": [
                            {
                                "entries": [
                                    {
                                        "ref_id": {"turn_index": 0, "ref_index": 1},
                                        "url": "https://ref.com/?utm_source=chatgpt.com",
                                        "attribution": "ref.com",
                                    }
                                ]
                            }
                        ],
                    }
                },
                "[ref.com](https://ref.com/)",
                "cite with UTM",
            ),
            (
                "\ue202turn0search1\ue201",
                {
                    "metadata": {
                        "content_references": [
                            {
                                "type": "grouped_webpages",
                                "url": "",
                                "items": [
                                    {
                                        "url": "https://ref.com/?ref=foo&utm_source=chatgpt.com",
                                        "attribution": "ref.com",
                                    }
                                ],
                                "matched_text": "\ue200cite\ue202search1\ue201",
                            }
                        ],
                        "search_result_groups": [
                            {
                                "entries": [
                                    {
                                        "ref_id": {"turn_index": 0, "ref_index": 1},
                                        "url": "https://ref.com/?ref=foo&utm_source=chatgpt.com",
                                        "attribution": "ref.com",
                                    }
                                ]
                            }
                        ],
                    }
                },
                "[ref.com](https://ref.com/?ref=foo)",
                "cite with UTM appended via &",
            ),
            (
                "\ue202turn0search1\ue201",
                {
                    "metadata": {
                        "search_result_groups": [
                            {
                                "entries": [
                                    {
                                        "ref_id": {"turn_index": 0, "ref_index": 1},
                                        "url": "https://orig.com/",
                                        "title": "Original Title",
                                    }
                                ]
                            }
                        ]
                    }
                },
                "[Original Title](https://orig.com/)",
                "original ref",
            ),
        ]
        for input_content, msg, expected, desc in cases:
            result = self.transform(input_content, msg)
            self.assertEqual(result, expected, f"Failed for: {desc}")


class TestMarkdown(unittest.TestCase):
    def setUp(self):
        from hippo.parsers.chatgpt import (
            Conversation,
            MessageNode,
            conversation_to_markdown,
            get_output_filename,
            compute_word_count,
        )

        self.Conversation = Conversation
        self.MessageNode = MessageNode
        self.to_markdown = conversation_to_markdown
        self.get_filename = get_output_filename
        self.word_count = compute_word_count

    def test_markdown_generation(self):
        cases = [
            # (conv, expected_in_output, description)
            (
                self.MessageNode("msg1", "user", "Hello", "2024-01-01", "text"),
                [
                    "id: test-id",
                    "title: Test",
                    "created_at: 2024-01-01",
                    "word_count: 1",
                    "- https://example.com",
                ],
                "frontmatter fields",
            ),
            (
                self.MessageNode(
                    "msg1", "user", "Hello world", "2024-01-01T10:30:00", "text"
                ),
                ["USER · 2024-01-01T10:30:00", "Hello world"],
                "message format",
            ),
            (
                self.MessageNode(
                    "msg1",
                    "assistant",
                    'print("hello")',
                    "2024-01-01",
                    "code",
                    language="python",
                ),
                ["```python", 'print("hello")', "```"],
                "code block",
            ),
            (
                self.MessageNode(
                    "msg2", "assistant", "Branch", "2024-01-01", "text", branch_depth=1
                ),
                ["└── ASSISTANT", "Branch"],
                "branch notation",
            ),
        ]

        for i, (msg, expected_strings, desc) in enumerate(cases):
            if i == 0:
                conv = self.Conversation(
                    id="test-id",
                    title="Test",
                    create_time=1700000000.0,
                    messages=[msg],
                    sources=["https://example.com"],
                )
                content = self.to_markdown(conv, None, 1, "2024-01-01", "2024-01-01")
            elif i == 3:
                main_msg = self.MessageNode(
                    "msg1", "user", "Main", "2024-01-01", "text"
                )
                conv = self.Conversation(
                    id="test", title="Test", create_time=0, messages=[main_msg, msg]
                )
                content = self.to_markdown(conv, "/path", 2, "2024-01-01", "2024-01-01")
            else:
                conv = self.Conversation(
                    id="test", title="Test", create_time=0, messages=[msg]
                )
                content = self.to_markdown(conv, "/path", 2, "2024-01-01", "2024-01-01")

            for exp in expected_strings:
                self.assertIn(exp, content, f"Failed for: {desc}, looking for: {exp}")

    def test_filename_and_wordcount(self):
        conv = self.Conversation(
            id="abc123",
            title="My Test Conversation",
            create_time=1700000000.0,
            messages=[],
        )
        filename = self.get_filename(conv)
        self.assertTrue(filename.startswith("my-test-conversation_"))
        self.assertTrue(filename.endswith(".md"))

        conv2 = self.Conversation(
            id="abc",
            title="Test",
            create_time=0,
            messages=[
                self.MessageNode("1", "user", "hello world", "2024-01-01", "text"),
                self.MessageNode(
                    "2", "assistant", "goodbye world", "2024-01-01", "text"
                ),
            ],
        )
        self.assertEqual(self.word_count(conv2), 4)


class TestLoad(unittest.TestCase):
    def test_load_multiple_conversations(self):
        from hippo.parsers.chatgpt import load_conversations

        data = [
            {"conversation_id": "1", "title": "A", "create_time": 1.0, "mapping": {}},
            {"conversation_id": "2", "title": "B", "create_time": 2.0, "mapping": {}},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        try:
            result = load_conversations(Path(temp_path))
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["conversation_id"], "1")
            self.assertEqual(result[1]["conversation_id"], "2")
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
