"""
Test suite for Anthropic messages.create output serialization.

This test suite verifies that we can correctly serialize and deserialize
Message response objects using real Anthropic SDK types, including:
- Complete response structure (id, type, role, model)
- Content blocks (text, thinking, tool_use, etc.)
- Usage statistics with cache information
- Optional fields (stop_reason, stop_sequence)
"""

import json
from anthropic.types.message import Message
from anthropic.types.text_block import TextBlock
from anthropic.types.thinking_block import ThinkingBlock
from anthropic.types.redacted_thinking_block import RedactedThinkingBlock
from anthropic.types.tool_use_block import ToolUseBlock
from anthropic.types.usage import Usage

from aco.runner.monkey_patching.api_parsers.anthropic_api_parser import (
    _get_output_anthropic_messages_create,
    _set_output_anthropic_messages_create,
)


def test_simple_text_response():
    """Test simple text response serialization."""
    # Create response using real Anthropic types
    text_block = TextBlock(
        type="text",
        text="Hello! How can I help you today?",
    )

    usage = Usage(
        input_tokens=10,
        output_tokens=20,
    )

    response = Message(
        id="msg_123abc",
        type="message",
        role="assistant",
        model="claude-3-5-sonnet-20241022",
        content=[text_block],
        stop_reason="end_turn",
        usage=usage,
    )

    # Serialize
    json_str = _get_output_anthropic_messages_create(response)

    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert parsed["id"] == "msg_123abc"
    assert parsed["type"] == "message"
    assert parsed["role"] == "assistant"
    assert parsed["model"] == "claude-3-5-sonnet-20241022"
    assert len(parsed["content"]) == 1
    assert parsed["content"][0]["type"] == "text"
    assert parsed["content"][0]["text"] == "Hello! How can I help you today?"
    assert parsed["stop_reason"] == "end_turn"
    assert parsed["usage"]["input_tokens"] == 10
    assert parsed["usage"]["output_tokens"] == 20

    # Deserialize
    new_response = Message(
        id="",
        type="message",
        role="assistant",
        model="",
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
    )
    _set_output_anthropic_messages_create(new_response, json_str)

    # Verify round-trip
    assert new_response.id == "msg_123abc"
    assert new_response.content[0].text == "Hello! How can I help you today?"
    assert new_response.usage.input_tokens == 10
    assert new_response.usage.output_tokens == 20


def test_response_with_tool_use():
    """Test response with tool use using real Anthropic types."""
    # Create tool use block
    tool_block = ToolUseBlock(
        type="tool_use",
        id="toolu_abc123",
        name="get_weather",
        input={"location": "San Francisco"},
    )

    response = Message(
        id="msg_456def",
        type="message",
        role="assistant",
        model="claude-3-5-sonnet-20241022",
        content=[tool_block],
        stop_reason="tool_use",
        usage=Usage(input_tokens=50, output_tokens=30),
    )

    # Serialize
    json_str = _get_output_anthropic_messages_create(response)

    # Verify
    parsed = json.loads(json_str)
    assert parsed["stop_reason"] == "tool_use"
    assert len(parsed["content"]) == 1
    assert parsed["content"][0]["type"] == "tool_use"
    assert parsed["content"][0]["name"] == "get_weather"
    assert parsed["content"][0]["input"]["location"] == "San Francisco"

    # Deserialize
    new_response = Message(
        id="",
        type="message",
        role="assistant",
        model="",
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
    )
    _set_output_anthropic_messages_create(new_response, json_str)

    # Verify round-trip
    assert new_response.stop_reason == "tool_use"
    assert new_response.content[0].name == "get_weather"
    assert new_response.content[0].input["location"] == "San Francisco"


def test_response_with_thinking_block():
    """Test response with thinking block (extended thinking models)."""
    text_block = TextBlock(
        type="text",
        text="Based on my analysis, the answer is 42.",
    )

    thinking_block = ThinkingBlock(
        type="thinking",
        thinking="Let me think about this carefully... The question asks about the meaning of life...",
        signature="sig_thinking_123",
    )

    usage = Usage(
        input_tokens=100,
        output_tokens=200,
    )

    response = Message(
        id="msg_thinking",
        type="message",
        role="assistant",
        model="claude-3-7-sonnet-20250219",
        content=[thinking_block, text_block],
        stop_reason="end_turn",
        usage=usage,
    )

    # Serialize
    json_str = _get_output_anthropic_messages_create(response)

    # Verify
    parsed = json.loads(json_str)
    assert len(parsed["content"]) == 2
    assert parsed["content"][0]["type"] == "thinking"
    assert "carefully" in parsed["content"][0]["thinking"]
    assert parsed["content"][0]["signature"] == "sig_thinking_123"
    assert parsed["content"][1]["type"] == "text"
    assert parsed["content"][1]["text"] == "Based on my analysis, the answer is 42."

    # Deserialize
    new_response = Message(
        id="",
        type="message",
        role="assistant",
        model="",
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
    )
    _set_output_anthropic_messages_create(new_response, json_str)

    # Verify round-trip
    assert len(new_response.content) == 2
    assert new_response.content[0].type == "thinking"
    assert new_response.content[0].signature == "sig_thinking_123"
    assert new_response.content[1].text == "Based on my analysis, the answer is 42."


def test_response_with_redacted_thinking():
    """Test response with redacted thinking block."""
    redacted_thinking = RedactedThinkingBlock(type="redacted_thinking", data="<redacted>")
    text_block = TextBlock(type="text", text="Here's my answer.")

    response = Message(
        id="msg_redacted",
        type="message",
        role="assistant",
        model="claude-3-7-sonnet-20250219",
        content=[redacted_thinking, text_block],
        stop_reason="end_turn",
        usage=Usage(input_tokens=50, output_tokens=25),
    )

    # Serialize
    json_str = _get_output_anthropic_messages_create(response)

    # Verify
    parsed = json.loads(json_str)
    assert len(parsed["content"]) == 2
    assert parsed["content"][0]["type"] == "redacted_thinking"
    assert parsed["content"][1]["type"] == "text"

    # Deserialize
    new_response = Message(
        id="",
        type="message",
        role="assistant",
        model="",
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
    )
    _set_output_anthropic_messages_create(new_response, json_str)

    # Verify round-trip
    assert new_response.content[0].type == "redacted_thinking"
    assert new_response.content[1].text == "Here's my answer."


def test_response_with_usage_details():
    """Test response with detailed usage statistics including cache."""
    from anthropic.types.cache_creation import CacheCreation
    from anthropic.types.server_tool_usage import ServerToolUsage

    cache_creation = CacheCreation(
        ephemeral_1h_input_tokens=100,
        ephemeral_5m_input_tokens=50,
    )

    server_tool_use = ServerToolUsage(
        web_search_requests=3,
    )

    usage = Usage(
        input_tokens=1000,
        output_tokens=500,
        cache_creation_input_tokens=200,
        cache_read_input_tokens=800,
        cache_creation=cache_creation,
        server_tool_use=server_tool_use,
    )

    text_block = TextBlock(
        type="text",
        text="Response using cached content.",
    )

    response = Message(
        id="msg_cached",
        type="message",
        role="assistant",
        model="claude-3-5-sonnet-20241022",
        content=[text_block],
        stop_reason="end_turn",
        usage=usage,
    )

    # Serialize
    json_str = _get_output_anthropic_messages_create(response)

    # Verify
    parsed = json.loads(json_str)
    assert parsed["usage"]["input_tokens"] == 1000
    assert parsed["usage"]["output_tokens"] == 500
    assert parsed["usage"]["cache_creation_input_tokens"] == 200
    assert parsed["usage"]["cache_read_input_tokens"] == 800
    assert parsed["usage"]["cache_creation"]["ephemeral_1h_input_tokens"] == 100
    assert parsed["usage"]["cache_creation"]["ephemeral_5m_input_tokens"] == 50
    assert parsed["usage"]["server_tool_use"]["web_search_requests"] == 3

    # Deserialize
    new_response = Message(
        id="",
        type="message",
        role="assistant",
        model="",
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
    )
    _set_output_anthropic_messages_create(new_response, json_str)

    # Verify round-trip
    assert new_response.usage.input_tokens == 1000
    assert new_response.usage.cache_creation_input_tokens == 200
    assert new_response.usage.cache_read_input_tokens == 800
    # Verify nested objects are properly reconstructed
    assert isinstance(new_response.usage.cache_creation, CacheCreation)
    assert new_response.usage.cache_creation.ephemeral_1h_input_tokens == 100
    assert new_response.usage.cache_creation.ephemeral_5m_input_tokens == 50
    assert isinstance(new_response.usage.server_tool_use, ServerToolUsage)
    assert new_response.usage.server_tool_use.web_search_requests == 3


def test_multiple_content_blocks():
    """Test response with multiple mixed content blocks."""
    blocks = [
        TextBlock(type="text", text="First, let me think about this."),
        ToolUseBlock(
            type="tool_use",
            id="tool_1",
            name="search",
            input={"query": "anthropic claude"},
        ),
        TextBlock(type="text", text="Based on the search results..."),
        ToolUseBlock(
            type="tool_use",
            id="tool_2",
            name="calculator",
            input={"expression": "2 + 2"},
        ),
        TextBlock(type="text", text="The answer is 4."),
    ]

    response = Message(
        id="msg_multi",
        type="message",
        role="assistant",
        model="claude-3-5-sonnet-20241022",
        content=blocks,
        stop_reason="end_turn",
        usage=Usage(input_tokens=200, output_tokens=150),
    )

    # Serialize
    json_str = _get_output_anthropic_messages_create(response)

    # Verify
    parsed = json.loads(json_str)
    assert len(parsed["content"]) == 5
    assert parsed["content"][0]["type"] == "text"
    assert parsed["content"][1]["type"] == "tool_use"
    assert parsed["content"][1]["name"] == "search"
    assert parsed["content"][3]["name"] == "calculator"
    assert parsed["content"][4]["text"] == "The answer is 4."

    # Deserialize
    new_response = Message(
        id="",
        type="message",
        role="assistant",
        model="",
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
    )
    _set_output_anthropic_messages_create(new_response, json_str)

    # Verify round-trip
    assert len(new_response.content) == 5
    assert new_response.content[1].name == "search"
    assert new_response.content[3].input["expression"] == "2 + 2"


def test_response_with_stop_sequence():
    """Test response that stopped on a stop sequence."""
    text_block = TextBlock(type="text", text="Here is the content before")

    response = Message(
        id="msg_stop",
        type="message",
        role="assistant",
        model="claude-3-5-sonnet-20241022",
        content=[text_block],
        stop_reason="stop_sequence",
        stop_sequence="\n\nHuman:",
        usage=Usage(input_tokens=30, output_tokens=10),
    )

    # Serialize
    json_str = _get_output_anthropic_messages_create(response)

    # Verify
    parsed = json.loads(json_str)
    assert parsed["stop_reason"] == "stop_sequence"
    assert parsed["stop_sequence"] == "\n\nHuman:"

    # Deserialize
    new_response = Message(
        id="",
        type="message",
        role="assistant",
        model="",
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
    )
    _set_output_anthropic_messages_create(new_response, json_str)

    # Verify round-trip
    assert new_response.stop_reason == "stop_sequence"
    assert new_response.stop_sequence == "\n\nHuman:"


def test_max_tokens_response():
    """Test response that stopped due to max_tokens."""
    text_block = TextBlock(
        type="text",
        text="This is a truncated response because we hit the",
    )

    response = Message(
        id="msg_maxtoken",
        type="message",
        role="assistant",
        model="claude-3-5-sonnet-20241022",
        content=[text_block],
        stop_reason="max_tokens",
        usage=Usage(input_tokens=50, output_tokens=100),
    )

    # Serialize
    json_str = _get_output_anthropic_messages_create(response)

    # Verify
    parsed = json.loads(json_str)
    assert parsed["stop_reason"] == "max_tokens"

    # Deserialize
    new_response = Message(
        id="",
        type="message",
        role="assistant",
        model="",
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
    )
    _set_output_anthropic_messages_create(new_response, json_str)

    # Verify round-trip
    assert new_response.stop_reason == "max_tokens"


def test_empty_text_response():
    """Test edge case with empty text content."""
    text_block = TextBlock(type="text", text="")

    response = Message(
        id="msg_empty",
        type="message",
        role="assistant",
        model="claude-3-5-sonnet-20241022",
        content=[text_block],
        stop_reason="end_turn",
        usage=Usage(input_tokens=10, output_tokens=1),
    )

    # Serialize
    json_str = _get_output_anthropic_messages_create(response)

    # Verify
    parsed = json.loads(json_str)
    assert parsed["content"][0]["text"] == ""

    # Deserialize
    new_response = Message(
        id="",
        type="message",
        role="assistant",
        model="",
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
    )
    _set_output_anthropic_messages_create(new_response, json_str)

    # Verify round-trip
    assert new_response.content[0].text == ""


def test_response_with_citations():
    """Test response with various citation types."""
    from anthropic.types.citation_char_location import CitationCharLocation
    from anthropic.types.citation_page_location import CitationPageLocation

    # Create text block with citations
    char_citation = CitationCharLocation(
        type="char_location",
        cited_text="This is cited text",
        document_index=0,
        start_char_index=100,
        end_char_index=120,
        document_title="Document Title",
        file_id="file_abc123",
    )

    page_citation = CitationPageLocation(
        type="page_location",
        cited_text="Another citation",
        document_index=1,
        start_page_number=5,
        end_page_number=6,
        document_title="Another Document",
    )

    text_block = TextBlock(
        type="text",
        text="Here is my answer with citations.",
        citations=[char_citation, page_citation],
    )

    response = Message(
        id="msg_citations",
        type="message",
        role="assistant",
        model="claude-3-5-sonnet-20241022",
        content=[text_block],
        stop_reason="end_turn",
        usage=Usage(input_tokens=100, output_tokens=50),
    )

    # Serialize
    json_str = _get_output_anthropic_messages_create(response)

    # Verify
    parsed = json.loads(json_str)
    assert len(parsed["content"][0]["citations"]) == 2
    assert parsed["content"][0]["citations"][0]["type"] == "char_location"
    assert parsed["content"][0]["citations"][0]["cited_text"] == "This is cited text"
    assert parsed["content"][0]["citations"][0]["start_char_index"] == 100
    assert parsed["content"][0]["citations"][1]["type"] == "page_location"
    assert parsed["content"][0]["citations"][1]["start_page_number"] == 5

    # Deserialize
    new_response = Message(
        id="",
        type="message",
        role="assistant",
        model="",
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
    )
    _set_output_anthropic_messages_create(new_response, json_str)

    # Verify round-trip - citations should be properly reconstructed
    assert len(new_response.content[0].citations) == 2
    assert isinstance(new_response.content[0].citations[0], CitationCharLocation)
    assert new_response.content[0].citations[0].cited_text == "This is cited text"
    assert new_response.content[0].citations[0].start_char_index == 100
    assert new_response.content[0].citations[0].file_id == "file_abc123"
    assert isinstance(new_response.content[0].citations[1], CitationPageLocation)
    assert new_response.content[0].citations[1].start_page_number == 5
    assert new_response.content[0].citations[1].end_page_number == 6


if __name__ == "__main__":
    test_simple_text_response()
    print("✓ test_simple_text_response")

    test_response_with_tool_use()
    print("✓ test_response_with_tool_use")

    test_response_with_thinking_block()
    print("✓ test_response_with_thinking_block")

    test_response_with_redacted_thinking()
    print("✓ test_response_with_redacted_thinking")

    test_response_with_usage_details()
    print("✓ test_response_with_usage_details")

    test_multiple_content_blocks()
    print("✓ test_multiple_content_blocks")

    test_response_with_stop_sequence()
    print("✓ test_response_with_stop_sequence")

    test_max_tokens_response()
    print("✓ test_max_tokens_response")

    test_empty_text_response()
    print("✓ test_empty_text_response")

    test_response_with_citations()
    print("✓ test_response_with_citations")

    print("\n✅ All output serialization tests passed!")
