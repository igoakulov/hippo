import unittest

from hippo.parsers.chatgpt import filter_conversations


class TestChatGPTSettings(unittest.TestCase):
    def test_include_content_types_defined(self):
        from hippo.parsers.chatgpt import INCLUDE_CONTENT_TYPES

        self.assertIn("text", INCLUDE_CONTENT_TYPES)
        self.assertIn("code", INCLUDE_CONTENT_TYPES)
        self.assertIn("execution_output", INCLUDE_CONTENT_TYPES)

    def test_exclude_content_types_defined(self):
        from hippo.parsers.chatgpt import EXCLUDE_CONTENT_TYPES

        self.assertIn("user_editable_context", EXCLUDE_CONTENT_TYPES)
        self.assertIn("thoughts", EXCLUDE_CONTENT_TYPES)
        self.assertIn("reasoning_recap", EXCLUDE_CONTENT_TYPES)


class TestShouldIncludeMessage(unittest.TestCase):
    def test_include_user_message(self):
        from hippo.parsers.chatgpt import should_include_message

        msg = {
            "author": {"role": "user"},
            "content": {"content_type": "text", "parts": ["hello"]},
            "metadata": {},
        }
        self.assertTrue(should_include_message(msg))

    def test_include_assistant_message(self):
        from hippo.parsers.chatgpt import should_include_message

        msg = {
            "author": {"role": "assistant"},
            "content": {"content_type": "text", "parts": ["response"]},
            "metadata": {},
        }
        self.assertTrue(should_include_message(msg))

    def test_exclude_system_message(self):
        from hippo.parsers.chatgpt import should_include_message

        msg = {
            "author": {"role": "system"},
            "content": {"content_type": "text", "parts": ["system"]},
            "metadata": {},
        }
        self.assertFalse(should_include_message(msg))

    def test_exclude_tool_message(self):
        from hippo.parsers.chatgpt import should_include_message

        msg = {
            "author": {"role": "tool", "name": "web"},
            "content": {"content_type": "text", "parts": ["tool"]},
            "metadata": {},
        }
        self.assertFalse(should_include_message(msg))

    def test_exclude_hidden_message(self):
        from hippo.parsers.chatgpt import should_include_message

        msg = {
            "author": {"role": "user"},
            "content": {"content_type": "text", "parts": ["hidden"]},
            "metadata": {"is_visually_hidden_from_conversation": True},
        }
        self.assertFalse(should_include_message(msg))

    def test_exclude_user_editable_context(self):
        from hippo.parsers.chatgpt import should_include_message

        msg = {
            "author": {"role": "user"},
            "content": {"content_type": "user_editable_context", "parts": ["profile"]},
            "metadata": {},
        }
        self.assertFalse(should_include_message(msg))

    def test_exclude_empty_content(self):
        from hippo.parsers.chatgpt import should_include_message

        msg = {
            "author": {"role": "assistant"},
            "content": {"content_type": "text", "parts": [""]},
            "metadata": {},
        }
        self.assertFalse(should_include_message(msg))

    def test_exclude_empty_code_content(self):
        from hippo.parsers.chatgpt import should_include_message

        msg = {
            "author": {"role": "assistant"},
            "content": {"content_type": "code", "text": "{}"},
            "metadata": {},
        }
        self.assertFalse(should_include_message(msg))


class TestParseConversationExpand(unittest.TestCase):
    def test_no_skip_when_no_last_id(self):
        from hippo.parsers.chatgpt import parse_conversation_expand

        conv_data = {
            "conversation_id": "test123",
            "title": "Test",
            "create_time": 1700000000.0,
            "mapping": {
                "root": {"id": "root", "parent": None, "children": ["msg1"]},
                "msg1": {
                    "id": "msg1",
                    "parent": "root",
                    "children": [],
                    "message": {
                        "id": "msg1",
                        "author": {"role": "user"},
                        "create_time": 1700000001.0,
                        "content": {"content_type": "text", "parts": ["hello"]},
                        "metadata": {},
                    },
                },
            },
        }

        conv = parse_conversation_expand(conv_data, None)
        self.assertEqual(len(conv.messages), 1)
        self.assertEqual(conv.messages[0].content, "hello")

    def test_skip_messages_before_last_id(self):
        from hippo.parsers.chatgpt import parse_conversation_expand

        conv_data = {
            "conversation_id": "test123",
            "title": "Test",
            "create_time": 1700000000.0,
            "mapping": {
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
            },
        }

        conv = parse_conversation_expand(conv_data, "msg1")
        self.assertEqual(len(conv.messages), 2)
        self.assertEqual(conv.messages[0].content, "second")
        self.assertEqual(conv.messages[1].content, "third")


class TestSlugify(unittest.TestCase):
    def test_get_output_filename_format(self):
        from hippo.parsers.chatgpt import Conversation, get_output_filename

        conv = Conversation(
            id="abc123",
            title="My Test Conversation",
            create_time=1700000000.0,
            messages=[],
        )
        filename = get_output_filename(conv)
        self.assertTrue(filename.startswith("my-test-conversation_"))
        self.assertTrue(filename.endswith(".md"))


class TestFilterConversations(unittest.TestCase):
    def setUp(self):
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

    def test_no_filters(self):
        result = filter_conversations(self.convs, None, None, None)
        self.assertEqual(len(result), 3)

    def test_filter_by_title(self):
        result = filter_conversations(self.convs, None, None, ["Test"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["conversation_id"], "1")
        self.assertEqual(result[1]["conversation_id"], "2")

    def test_filter_by_from_time(self):
        result = filter_conversations(self.convs, 1700100000.0, None, None)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["conversation_id"], "2")
        self.assertEqual(result[1]["conversation_id"], "3")

    def test_filter_by_till_time(self):
        result = filter_conversations(self.convs, None, 1700100000.0, None)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["conversation_id"], "1")
        self.assertEqual(result[1]["conversation_id"], "2")

    def test_filter_by_time_range(self):
        result = filter_conversations(self.convs, 1700100000.0, 1700100000.0, None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["conversation_id"], "2")

    def test_filter_by_multiple_titles(self):
        result = filter_conversations(
            self.convs, None, None, ["Conversation A", "Conversation B"]
        )
        self.assertEqual(len(result), 2)

    def test_combined_filters(self):
        result = filter_conversations(self.convs, 1700000000.0, 1700050000.0, ["Test"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["conversation_id"], "1")


class TestComputeWordCount(unittest.TestCase):
    def test_word_count(self):
        from hippo.parsers.chatgpt import Conversation, MessageNode, compute_word_count

        conv = Conversation(
            id="abc",
            title="Test",
            create_time=0,
            messages=[
                MessageNode("1", "user", "hello world", "2024-01-01", "text"),
                MessageNode("2", "assistant", "goodbye world", "2024-01-01", "text"),
            ],
        )
        count = compute_word_count(conv)
        self.assertEqual(count, 4)


class TestConversationToMarkdown(unittest.TestCase):
    def test_frontmatter_fields(self):
        from hippo.parsers.chatgpt import (
            Conversation,
            MessageNode,
            conversation_to_markdown,
        )

        conv = Conversation(
            id="test-id-123",
            title="Test Title",
            create_time=1700000000.0,
            messages=[
                MessageNode("msg1", "user", "Hello", "2024-01-01", "text"),
            ],
        )

        content = conversation_to_markdown(
            conv, "/path/to/export.json", 1, "2024-01-01", "2024-01-02"
        )

        self.assertIn("id: test-id-123", content)
        self.assertIn("title: Test Title", content)
        self.assertIn("created_at: 2024-01-01", content)
        self.assertIn("updated_at: 2024-01-02", content)
        self.assertIn("original_conversation_created_at:", content)
        self.assertIn("word_count: 1", content)
        self.assertIn("- /path/to/export.json", content)

    def test_message_format(self):
        from hippo.parsers.chatgpt import (
            Conversation,
            MessageNode,
            conversation_to_markdown,
        )

        conv = Conversation(
            id="test",
            title="Test",
            create_time=0,
            messages=[
                MessageNode(
                    "msg1", "user", "Hello world", "2024-01-01T10:30:00", "text"
                ),
                MessageNode(
                    "msg2", "assistant", "Hi there", "2024-01-01T10:30:01", "text"
                ),
            ],
        )

        content = conversation_to_markdown(conv, "/path", 2, "2024-01-01", "2024-01-01")

        self.assertIn("USER · 2024-01-01T10:30:00", content)
        self.assertIn("Hello world", content)
        self.assertIn("ASSISTANT · 2024-01-01T10:30:01", content)
        self.assertIn("Hi there", content)

    def test_code_block(self):
        from hippo.parsers.chatgpt import (
            Conversation,
            MessageNode,
            conversation_to_markdown,
        )

        conv = Conversation(
            id="test",
            title="Test",
            create_time=0,
            messages=[
                MessageNode(
                    "msg1",
                    "assistant",
                    'print("hello")',
                    "2024-01-01",
                    "code",
                    language="python",
                ),
            ],
        )

        content = conversation_to_markdown(conv, "/path", 2, "2024-01-01", "2024-01-01")

        self.assertIn("```python", content)
        self.assertIn('print("hello")', content)
        self.assertIn("```", content)

    def test_branch_indentation(self):
        from hippo.parsers.chatgpt import (
            Conversation,
            MessageNode,
            conversation_to_markdown,
        )

        conv = Conversation(
            id="test",
            title="Test",
            create_time=0,
            messages=[
                MessageNode("msg1", "user", "Main path", "2024-01-01", "text"),
                MessageNode(
                    "msg2",
                    "assistant",
                    "Branch response",
                    "2024-01-01",
                    "text",
                    branch_depth=1,
                ),
            ],
        )

        content = conversation_to_markdown(conv, "/path", 2, "2024-01-01", "2024-01-01")

        self.assertIn("> ASSISTANT · 2024-01-01", content)
        self.assertIn("> Branch response", content)


if __name__ == "__main__":
    unittest.main()
