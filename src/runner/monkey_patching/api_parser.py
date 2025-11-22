from typing import Any, Dict, List, Tuple
from aco.runner.monkey_patching.api_parsers.openai_api_parser import (
    _get_input_openai_responses_create,
    _get_input_openai_chat_completions_create,
    _get_output_openai,
    _set_input_openai,
    _set_output_openai,
    _get_model_openai,
)
from aco.runner.monkey_patching.api_parsers.anthropic_api_parser import (
    _get_input_anthropic_messages_create,
    _set_input_anthropic_messages_create,
    _get_output_anthropic_messages_create,
    _set_output_anthropic_messages_create,
    _get_model_anthropic_messages_create,
)
from aco.runner.monkey_patching.api_parsers.vertex_api_parser import (
    _get_input_vertex_client_models_generate_content,
    _set_input_vertex_client_models_generate_content,
    _get_output_vertex_client_models_generate_content,
    _set_output_vertex_client_models_generate_content,
    _get_model_vertex_client_models_generate_content,
)
from aco.runner.monkey_patching.api_parsers.together_parser import (
    _get_input_together_resources_chat_completions_ChatCompletions_create,
    _set_input_together_resources_chat_completions_ChatCompletions_create,
    _get_output_together_resources_chat_completions_ChatCompletions_create,
    _set_output_together_resources_chat_completions_ChatCompletions_create,
    _get_model_together_resources_chat_completions_ChatCompletions_create,
)
from aco.runner.monkey_patching.api_parsers.mcp_api_parser import (
    _get_input_mcp_client_session_call_tool,
    _set_input_mcp_client_session_call_tool,
    _get_output_mcp_client_session_call_tool,
    _set_output_mcp_client_session_call_tool,
    _get_model_mcp_client_session_call_tool,
)


def get_input(input_dict: Dict[str, Any], api_type: str) -> Tuple[str, List[str]]:
    """Extract input text and attachments from API input."""
    if api_type in ["OpenAI.chat.completions.create", "AsyncOpenAI.chat.completions.create"]:
        return _get_input_openai_chat_completions_create(input_dict)
    elif api_type in ["OpenAI.responses.create", "AsyncOpenAI.responses.create"]:
        return _get_input_openai_responses_create(input_dict)
    elif api_type == "OpenAI.beta.threads.create":
        raise NotImplementedError(f"get_input not implemented for {api_type}")
    elif api_type == "OpenAI.beta.threads.create_and_poll":
        raise NotImplementedError(f"get_input not implemented for {api_type}")
    elif api_type == "Anthropic.messages.create":
        return _get_input_anthropic_messages_create(input_dict)
    elif api_type == "vertexai client_models_generate_content":
        return _get_input_vertex_client_models_generate_content(input_dict)
    elif api_type == "together.resources.chat.completions.ChatCompletions.create":
        return _get_input_together_resources_chat_completions_ChatCompletions_create(input_dict)
    elif api_type == "MCP.ClientSession.call_tool":
        return _get_input_mcp_client_session_call_tool(input_dict)
    else:
        raise ValueError(f"Unknown API type {api_type}")


def set_input(input_dict: Dict[str, Any], new_input_text: str, api_type: str) -> None:
    """Returns pickle with changed input text."""
    if api_type in [
        "OpenAI.chat.completions.create",
        "AsyncOpenAI.chat.completions.create",
        "OpenAI.responses.create",
        "AsyncOpenAI.responses.create",
    ]:
        return _set_input_openai(input_dict, new_input_text)
    elif api_type == "OpenAI.beta.threads.create":
        raise NotImplementedError(f"set_input not implemented for {api_type}")
    elif api_type == "Anthropic.messages.create":
        return _set_input_anthropic_messages_create(input_dict, new_input_text)
    elif api_type == "vertexai client_models_generate_content":
        return _set_input_vertex_client_models_generate_content(input_dict, new_input_text)
    elif api_type == "together.resources.chat.completions.ChatCompletions.create":
        return _set_input_together_resources_chat_completions_ChatCompletions_create(
            input_dict, new_input_text
        )
    elif api_type == "MCP.ClientSession.call_tool":
        return _set_input_mcp_client_session_call_tool(input_dict, new_input_text)
    else:
        raise ValueError(f"Unknown API type {api_type}")


def get_output(response_obj: Any, api_type: str) -> str:
    if api_type in [
        "OpenAI.chat.completions.create",
        "AsyncOpenAI.chat.completions.create",
        "OpenAI.responses.create",
        "AsyncOpenAI.responses.create",
    ]:
        return _get_output_openai(response_obj)
    elif api_type == "OpenAI.beta.threads.create_and_poll":
        raise NotImplementedError(f"get_output not implemented for {api_type}")
    elif api_type == "Anthropic.messages.create":
        return _get_output_anthropic_messages_create(response_obj)
    elif api_type == "vertexai client_models_generate_content":
        return _get_output_vertex_client_models_generate_content(response_obj)
    elif api_type == "together.resources.chat.completions.ChatCompletions.create":
        return _get_output_together_resources_chat_completions_ChatCompletions_create(response_obj)
    elif api_type == "MCP.ClientSession.call_tool":
        return _get_output_mcp_client_session_call_tool(response_obj)
    else:
        raise ValueError(f"Unknown API type {api_type}")


def set_output(original_output_obj: Any, new_output_text: str, api_type):
    if api_type in [
        "OpenAI.chat.completions.create",
        "AsyncOpenAI.chat.completions.create",
        "OpenAI.responses.create",
        "AsyncOpenAI.responses.create",
    ]:
        return _set_output_openai(original_output_obj, new_output_text)
    elif api_type == "OpenAI.beta.threads.create_and_poll":
        raise NotImplementedError(f"set_output not implemented for {api_type}")
    elif api_type == "Anthropic.messages.create":
        return _set_output_anthropic_messages_create(original_output_obj, new_output_text)
    elif api_type == "vertexai client_models_generate_content":
        return _set_output_vertex_client_models_generate_content(
            original_output_obj, new_output_text
        )
    elif api_type == "together.resources.chat.completions.ChatCompletions.create":
        return _set_output_together_resources_chat_completions_ChatCompletions_create(
            original_output_obj, new_output_text
        )
    elif api_type == "MCP.ClientSession.call_tool":
        return _set_output_mcp_client_session_call_tool(original_output_obj, new_output_text)
    else:
        raise ValueError(f"Unknown API type {api_type}")


def get_model_name(input_dict: Dict[str, Any], api_type: str) -> str:
    if api_type in [
        "OpenAI.chat.completions.create",
        "AsyncOpenAI.chat.completions.create",
        "OpenAI.responses.create",
        "AsyncOpenAI.responses.create",
    ]:
        return _get_model_openai(input_dict)
    elif api_type == "OpenAI.beta.threads.create_and_poll":
        raise NotImplementedError(f"get_model_name not implemented for {api_type}")
    elif api_type == "OpenAI.beta.threads.create":
        raise NotImplementedError(f"get_model_name not implemented for {api_type}")
    elif api_type == "Anthropic.messages.create":
        return _get_model_anthropic_messages_create(input_dict)
    elif api_type == "vertexai client_models_generate_content":
        return _get_model_vertex_client_models_generate_content(input_dict)
    elif api_type == "together.resources.chat.completions.ChatCompletions.create":
        return _get_model_together_resources_chat_completions_ChatCompletions_create(input_dict)
    elif api_type == "MCP.ClientSession.call_tool":
        return _get_model_mcp_client_session_call_tool(input_dict)
    else:
        raise ValueError(f"Unknown API type {api_type}")
