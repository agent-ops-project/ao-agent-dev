import json
from typing import Any, Dict, List, Tuple
from aco.runner.monkey_patching.api_parsers.api_parser_utils import _deep_serialize


# --------------------- Helper functions ---------------------


def _serialize_content_block(block: Any) -> Dict[str, Any]:
    """Serialize a ContentBlock to JSON-compatible format.

    ContentBlock can be:
    - TextBlock: {type: "text", text: str, citations: Optional[List[TextCitation]]}
    - ThinkingBlock: {type: "thinking", thinking: str, signature: str}
    - RedactedThinkingBlock: {type: "redacted_thinking"}
    - ToolUseBlock: {type: "tool_use", id: str, name: str, input: object}
    - ServerToolUseBlock: {type: "server_tool_use", ...}
    - WebSearchToolResultBlock: {type: "web_search_tool_result", ...}
    """
    if hasattr(block, "__dict__"):
        return _deep_serialize(block)
    elif isinstance(block, dict):
        return block
    else:
        return {"type": "unknown", "content": str(block)}


def _serialize_usage(usage: Any) -> Dict[str, Any]:
    """Serialize Usage to JSON-compatible format."""
    if usage is None:
        return None

    if hasattr(usage, "__dict__"):
        return _deep_serialize(usage)
    elif isinstance(usage, dict):
        return usage
    else:
        return {"input_tokens": 0, "output_tokens": 0}


# --------------------- API parsers ---------------------


def _get_input_anthropic_messages_create(
    input_dict: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """Serialize Anthropic messages.create input to JSON string.

    Returns:
        Tuple of (json_str, attachments):
        - json_str: JSON representation of the input
        - attachments: List of attachment file IDs referenced in messages (empty for now)
    """
    from anthropic._types import NOT_GIVEN

    serialized = {}
    attachments = []

    # Serialize all fields, handling NOT_GIVEN sentinel
    for key, value in input_dict.items():
        if value is NOT_GIVEN:
            serialized[key] = "NOT_GIVEN"
        elif key == "messages":
            # Serialize messages array
            serialized[key] = []
            for msg in value:
                if isinstance(msg, dict):
                    serialized_msg = {}
                    serialized_msg["role"] = msg.get("role", "user")

                    # Handle content - can be string or list of content blocks
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        serialized_msg["content"] = content
                    elif isinstance(content, list):
                        serialized_msg["content"] = [_deep_serialize(c) for c in content]
                    else:
                        serialized_msg["content"] = _deep_serialize(content)

                    serialized[key].append(serialized_msg)
                else:
                    # Object with attributes
                    serialized[key].append(_deep_serialize(msg))
        else:
            # Deep serialize everything else
            serialized[key] = _deep_serialize(value)

    json_str = json.dumps(serialized, indent=2, ensure_ascii=False)
    return json_str, attachments


def _set_input_anthropic_messages_create(
    original_input_dict: Dict[str, Any], new_input_text: str
) -> None:
    """Deserialize JSON string back to Anthropic messages.create input dict.

    This updates the original_input_dict in-place with values from the JSON string.
    Handles reconstruction of NOT_GIVEN sentinels and proper message structures.
    """
    from anthropic._types import NOT_GIVEN

    # Parse JSON
    new_data = json.loads(new_input_text)

    # Clear the original dict and repopulate it
    original_input_dict.clear()

    # Restore all fields, handling NOT_GIVEN sentinel
    for key, value in new_data.items():
        if value == "NOT_GIVEN":
            original_input_dict[key] = NOT_GIVEN
        else:
            original_input_dict[key] = value


def _get_output_anthropic_messages_create(response_obj: Any) -> str:
    """Serialize complete Anthropic Message response to JSON string.

    Returns a JSON string representation of the entire Message object
    that can be deserialized back to its original form.
    """
    from anthropic.types.message import Message

    response_obj: Message
    serialized = {}

    # Required fields - Message always has these
    serialized["id"] = response_obj.id
    serialized["type"] = response_obj.type
    serialized["role"] = response_obj.role
    serialized["model"] = response_obj.model

    # Content blocks
    serialized["content"] = [_serialize_content_block(block) for block in response_obj.content]

    # Optional fields
    if response_obj.stop_reason is not None:
        serialized["stop_reason"] = response_obj.stop_reason

    if response_obj.stop_sequence is not None:
        serialized["stop_sequence"] = response_obj.stop_sequence

    # Usage information
    if response_obj.usage is not None:
        serialized["usage"] = _serialize_usage(response_obj.usage)

    # Convert to JSON string
    return json.dumps(serialized, indent=2, ensure_ascii=False)


def _set_output_anthropic_messages_create(original_output_obj: Any, output_text: str) -> None:
    """Deserialize JSON string back to Anthropic Message response object.

    This updates the original_output_obj in-place with values from the JSON string.
    """
    from anthropic.types.message import Message
    from anthropic.types.text_block import TextBlock
    from anthropic.types.thinking_block import ThinkingBlock
    from anthropic.types.redacted_thinking_block import RedactedThinkingBlock
    from anthropic.types.tool_use_block import ToolUseBlock
    from anthropic.types.usage import Usage
    from anthropic.types.citation_char_location import CitationCharLocation
    from anthropic.types.citation_page_location import CitationPageLocation
    from anthropic.types.citation_content_block_location import CitationContentBlockLocation
    from anthropic.types.citations_web_search_result_location import (
        CitationsWebSearchResultLocation,
    )
    from anthropic.types.citations_search_result_location import CitationsSearchResultLocation

    # Parse JSON
    new_data = json.loads(output_text)

    # Update required fields
    original_output_obj: Message
    original_output_obj.id = new_data["id"]
    original_output_obj.type = new_data["type"]
    original_output_obj.role = new_data["role"]
    original_output_obj.model = new_data["model"]

    # Update optional fields
    original_output_obj.stop_reason = new_data.get("stop_reason", None)
    original_output_obj.stop_sequence = new_data.get("stop_sequence", None)

    # Helper function to reconstruct citations
    def reconstruct_citations(citations_data):
        if not citations_data:
            return None

        citations = []
        for citation_data in citations_data:
            citation_type = citation_data.get("type")

            if citation_type == "char_location":
                citation = CitationCharLocation(**citation_data)
            elif citation_type == "page_location":
                citation = CitationPageLocation(**citation_data)
            elif citation_type == "content_block_location":
                citation = CitationContentBlockLocation(**citation_data)
            elif citation_type == "web_search_result_location":
                citation = CitationsWebSearchResultLocation(**citation_data)
            elif citation_type == "search_result_location":
                citation = CitationsSearchResultLocation(**citation_data)
            else:
                # Unknown citation type - preserve as dict
                citation = citation_data

            citations.append(citation)

        return citations

    # Update content blocks - reconstruct based on type
    content_blocks = []
    for block_data in new_data["content"]:
        block_type = block_data.get("type")

        if block_type == "text":
            citations = reconstruct_citations(block_data.get("citations"))
            block = TextBlock(text=block_data["text"], type="text", citations=citations)
            content_blocks.append(block)
        elif block_type == "thinking":
            block = ThinkingBlock(
                thinking=block_data["thinking"], signature=block_data["signature"], type="thinking"
            )
            content_blocks.append(block)
        elif block_type == "redacted_thinking":
            block = RedactedThinkingBlock(
                type="redacted_thinking", data=block_data.get("data", "<redacted>")
            )
            content_blocks.append(block)
        elif block_type == "tool_use":
            block = ToolUseBlock(
                id=block_data["id"],
                name=block_data["name"],
                input=block_data["input"],
                type="tool_use",
            )
            content_blocks.append(block)
        else:
            # For other block types (ServerToolUseBlock, WebSearchToolResultBlock, etc.)
            # we'll use a generic approach - just preserve the dict structure
            # This is safe because Pydantic models can be constructed from dicts
            content_blocks.append(block_data)

    original_output_obj.content = content_blocks

    # Update usage
    if "usage" in new_data and new_data["usage"]:
        from anthropic.types.cache_creation import CacheCreation
        from anthropic.types.server_tool_usage import ServerToolUsage

        usage_data = new_data["usage"]

        # Reconstruct cache_creation if present
        cache_creation = None
        if usage_data.get("cache_creation"):
            cache_creation = CacheCreation(**usage_data["cache_creation"])

        # Reconstruct server_tool_use if present
        server_tool_use = None
        if usage_data.get("server_tool_use"):
            server_tool_use = ServerToolUsage(**usage_data["server_tool_use"])

        original_output_obj.usage = Usage(
            input_tokens=usage_data["input_tokens"],
            output_tokens=usage_data["output_tokens"],
            cache_creation_input_tokens=usage_data.get("cache_creation_input_tokens"),
            cache_read_input_tokens=usage_data.get("cache_read_input_tokens"),
            cache_creation=cache_creation,
            server_tool_use=server_tool_use,
            service_tier=usage_data.get("service_tier"),
        )


def _get_model_anthropic_messages_create(input_dict: Dict[str, Any]) -> str:
    return input_dict.get("model", "unknown")
