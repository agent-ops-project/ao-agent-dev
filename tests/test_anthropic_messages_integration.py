"""
Integration tests for Anthropic messages.create with real Anthropic SDK types.

This test suite verifies that our serialization works correctly with actual
Anthropic SDK objects (not just dicts), including handling of Pydantic models,
special types, and the NOT_GIVEN sentinel.
"""

import json
from anthropic._types import NOT_GIVEN

from aco.runner.monkey_patching.api_parsers.anthropic_api_parser import (
    _get_input_anthropic_messages_create,
    _set_input_anthropic_messages_create,
)


def test_with_not_given_sentinel():
    """Test handling of Anthropic's NOT_GIVEN sentinel value."""
    input_dict = {
        "messages": [{"role": "user", "content": "Hello"}],
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
        "temperature": NOT_GIVEN,  # NOT_GIVEN sentinel
        "top_p": NOT_GIVEN,
        "top_k": NOT_GIVEN,
    }

    # Serialize
    json_str, _, _ = _get_input_anthropic_messages_create(input_dict)

    # Verify NOT_GIVEN is serialized as string
    parsed = json.loads(json_str)
    assert parsed["temperature"] == "NOT_GIVEN"
    assert parsed["top_p"] == "NOT_GIVEN"
    assert parsed["top_k"] == "NOT_GIVEN"
    assert parsed["max_tokens"] == 1024  # Regular value preserved

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify NOT_GIVEN is restored
    assert new_input_dict["max_tokens"] == 1024
    # NOT_GIVEN should be restored to the actual sentinel
    from anthropic._types import NOT_GIVEN as restored_sentinel

    assert new_input_dict["temperature"] == restored_sentinel
    assert new_input_dict["top_p"] == restored_sentinel


def test_complete_api_call_structure():
    """Test with a realistic complete API call structure."""
    input_dict = {
        "messages": [
            {"role": "user", "content": "What's the weather like in San Francisco?"},
        ],
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 40,
        "metadata": {"user_id": "test_user_123"},
        "stop_sequences": ["\n\nHuman:", "\n\nAssistant:"],
        "tools": [
            {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city name",
                        }
                    },
                    "required": ["location"],
                },
            }
        ],
        "tool_choice": {"type": "auto"},
    }

    # Serialize
    json_str, attachments, tools = _get_input_anthropic_messages_create(input_dict)

    # Verify
    parsed = json.loads(json_str)
    assert len(parsed["messages"]) == 1
    assert parsed["model"] == "claude-3-5-sonnet-20241022"
    assert parsed["max_tokens"] == 1024
    assert parsed["temperature"] == 1.0
    assert parsed["top_k"] == 40
    assert len(parsed["tools"]) == 1
    assert "get_weather" in tools
    assert len(parsed["stop_sequences"]) == 2

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify round-trip
    assert new_input_dict["model"] == "claude-3-5-sonnet-20241022"
    assert new_input_dict["temperature"] == 1.0
    assert new_input_dict["tools"][0]["name"] == "get_weather"
    assert new_input_dict["metadata"]["user_id"] == "test_user_123"


def test_system_message_as_string():
    """Test system message provided as simple string."""
    input_dict = {
        "messages": [{"role": "user", "content": "Hello"}],
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 100,
        "system": "You are a helpful assistant that speaks like a pirate.",
    }

    # Serialize
    json_str, _, _ = _get_input_anthropic_messages_create(input_dict)

    # Verify
    parsed = json.loads(json_str)
    assert parsed["system"] == "You are a helpful assistant that speaks like a pirate."

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify round-trip
    assert new_input_dict["system"] == "You are a helpful assistant that speaks like a pirate."


def test_system_message_as_blocks():
    """Test system message provided as content blocks."""
    input_dict = {
        "messages": [{"role": "user", "content": "Analyze this"}],
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 500,
        "system": [
            {"type": "text", "text": "You are an expert analyst."},
            {
                "type": "text",
                "text": "Always provide detailed explanations.",
                "cache_control": {"type": "ephemeral"},
            },
        ],
    }

    # Serialize
    json_str, _, _ = _get_input_anthropic_messages_create(input_dict)

    # Verify
    parsed = json.loads(json_str)
    assert isinstance(parsed["system"], list)
    assert len(parsed["system"]) == 2
    assert parsed["system"][0]["text"] == "You are an expert analyst."
    assert parsed["system"][1]["cache_control"]["type"] == "ephemeral"

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify round-trip
    assert len(new_input_dict["system"]) == 2
    assert new_input_dict["system"][0]["text"] == "You are an expert analyst."


def test_multimodal_message_with_images():
    """Test message with image content blocks."""
    input_dict = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                        },
                    },
                ],
            }
        ],
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
    }

    # Serialize
    json_str, _, _ = _get_input_anthropic_messages_create(input_dict)

    # Verify
    parsed = json.loads(json_str)
    content = parsed["messages"][0]["content"]
    assert len(content) == 2
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image"
    assert content[1]["source"]["type"] == "base64"
    assert content[1]["source"]["media_type"] == "image/png"

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify round-trip
    new_content = new_input_dict["messages"][0]["content"]
    assert len(new_content) == 2
    assert new_content[0]["text"] == "What's in this image?"
    assert new_content[1]["source"]["media_type"] == "image/png"


def test_assistant_message_with_tool_use():
    """Test assistant message with tool use in conversation."""
    input_dict = {
        "messages": [
            {"role": "user", "content": "What's the weather in NYC?"},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_01A09q90qw90lq917835lq9",
                        "name": "get_weather",
                        "input": {"location": "New York City"},
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
                        "content": "It's 72°F and sunny",
                    }
                ],
            },
        ],
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 512,
    }

    # Serialize
    json_str, _, _ = _get_input_anthropic_messages_create(input_dict)

    # Verify
    parsed = json.loads(json_str)
    assert len(parsed["messages"]) == 3
    assert parsed["messages"][1]["role"] == "assistant"
    assert parsed["messages"][1]["content"][0]["type"] == "tool_use"
    assert parsed["messages"][1]["content"][0]["name"] == "get_weather"
    assert parsed["messages"][2]["content"][0]["type"] == "tool_result"

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify round-trip
    assert len(new_input_dict["messages"]) == 3
    assert new_input_dict["messages"][1]["content"][0]["input"]["location"] == "New York City"
    assert "sunny" in new_input_dict["messages"][2]["content"][0]["content"]


def test_thinking_config():
    """Test with thinking config for extended thinking models."""
    input_dict = {
        "messages": [{"role": "user", "content": "Solve this complex problem: ..."}],
        "model": "claude-3-7-sonnet-20250219",
        "max_tokens": 4096,
        "thinking": {
            "type": "enabled",
            "budget_tokens": 2000,
        },
    }

    # Serialize
    json_str, _, _ = _get_input_anthropic_messages_create(input_dict)

    # Verify
    parsed = json.loads(json_str)
    assert parsed["thinking"]["type"] == "enabled"
    assert parsed["thinking"]["budget_tokens"] == 2000

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify round-trip
    assert new_input_dict["thinking"]["type"] == "enabled"
    assert new_input_dict["thinking"]["budget_tokens"] == 2000


def test_message_with_document_content():
    """Test message with document content block."""
    input_dict = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Summarize this document:"},
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": "JVBERi0xLjQKJeLjz9MK...",
                        },
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
            }
        ],
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 2048,
    }

    # Serialize
    json_str, _, _ = _get_input_anthropic_messages_create(input_dict)

    # Verify
    parsed = json.loads(json_str)
    content = parsed["messages"][0]["content"]
    assert len(content) == 2
    assert content[1]["type"] == "document"
    assert content[1]["source"]["media_type"] == "application/pdf"
    assert content[1]["cache_control"]["type"] == "ephemeral"

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify round-trip
    new_content = new_input_dict["messages"][0]["content"]
    assert new_content[1]["source"]["media_type"] == "application/pdf"


def test_prefilled_assistant_response():
    """Test prefilling assistant response (forcing specific output start)."""
    input_dict = {
        "messages": [
            {"role": "user", "content": "Write a haiku about clouds"},
            {"role": "assistant", "content": "Here is a haiku:\n\nWhite cotton"},
        ],
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 256,
    }

    # Serialize
    json_str, _, _ = _get_input_anthropic_messages_create(input_dict)

    # Verify
    parsed = json.loads(json_str)
    assert parsed["messages"][1]["role"] == "assistant"
    assert parsed["messages"][1]["content"] == "Here is a haiku:\n\nWhite cotton"

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify round-trip
    assert new_input_dict["messages"][1]["content"] == "Here is a haiku:\n\nWhite cotton"


def test_with_multiple_tools():
    """Test with multiple tool definitions."""
    input_dict = {
        "messages": [{"role": "user", "content": "Help me with various tasks"}],
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
        "tools": [
            {
                "name": "calculator",
                "description": "Perform calculations",
                "input_schema": {
                    "type": "object",
                    "properties": {"expression": {"type": "string"}},
                    "required": ["expression"],
                },
            },
            {
                "name": "search",
                "description": "Search the web",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "name": "file_read",
                "description": "Read a file",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        ],
    }

    # Serialize
    json_str, _, tools = _get_input_anthropic_messages_create(input_dict)

    # Verify
    parsed = json.loads(json_str)
    assert len(parsed["tools"]) == 3
    assert len(tools) == 3
    assert "calculator" in tools
    assert "search" in tools
    assert "file_read" in tools

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify round-trip
    assert len(new_input_dict["tools"]) == 3
    assert new_input_dict["tools"][0]["name"] == "calculator"
    assert new_input_dict["tools"][2]["name"] == "file_read"


def test_with_tool_choice_specific():
    """Test with specific tool choice."""
    input_dict = {
        "messages": [{"role": "user", "content": "Calculate 2 + 2"}],
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 512,
        "tools": [
            {
                "name": "calculator",
                "description": "Perform calculations",
                "input_schema": {
                    "type": "object",
                    "properties": {"expression": {"type": "string"}},
                },
            }
        ],
        "tool_choice": {"type": "tool", "name": "calculator"},
    }

    # Serialize
    json_str, _, _ = _get_input_anthropic_messages_create(input_dict)

    # Verify
    parsed = json.loads(json_str)
    assert parsed["tool_choice"]["type"] == "tool"
    assert parsed["tool_choice"]["name"] == "calculator"

    # Deserialize
    new_input_dict = {}
    _set_input_anthropic_messages_create(new_input_dict, json_str)

    # Verify round-trip
    assert new_input_dict["tool_choice"]["type"] == "tool"
    assert new_input_dict["tool_choice"]["name"] == "calculator"


if __name__ == "__main__":
    test_with_not_given_sentinel()
    print("✓ test_with_not_given_sentinel")

    test_complete_api_call_structure()
    print("✓ test_complete_api_call_structure")

    test_system_message_as_string()
    print("✓ test_system_message_as_string")

    test_system_message_as_blocks()
    print("✓ test_system_message_as_blocks")

    test_multimodal_message_with_images()
    print("✓ test_multimodal_message_with_images")

    test_assistant_message_with_tool_use()
    print("✓ test_assistant_message_with_tool_use")

    test_thinking_config()
    print("✓ test_thinking_config")

    test_message_with_document_content()
    print("✓ test_message_with_document_content")

    test_prefilled_assistant_response()
    print("✓ test_prefilled_assistant_response")

    test_with_multiple_tools()
    print("✓ test_with_multiple_tools")

    test_with_tool_choice_specific()
    print("✓ test_with_tool_choice_specific")

    print("\n✅ All integration tests passed!")
