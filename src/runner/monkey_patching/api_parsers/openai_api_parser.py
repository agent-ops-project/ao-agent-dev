import json
from typing import Any, Dict, List, Tuple


def _func_kwargs_to_json_str_openai_responses_create(
    input_dict: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """Extract input text and attachments from OpenAI responses create input."""
    from openai._utils._transform import maybe_transform
    from openai.types.responses import response_create_params

    json_dict = maybe_transform(
        {
            "input": input_dict.get("input"),
            "model": input_dict.get("model"),
            "include": input_dict.get("include"),
            "instructions": input_dict.get("instructions"),
            "max_output_tokens": input_dict.get("max_output_tokens"),
            "metadata": input_dict.get("metadata"),
            "parallel_tool_calls": input_dict.get("parallel_tool_calls"),
            "previous_response_id": input_dict.get("previous_response_id"),
            "reasoning": input_dict.get("reasoning"),
            "service_tier": input_dict.get("service_tier"),
            "store": input_dict.get("store"),
            "stream": input_dict.get("stream"),
            "temperature": input_dict.get("temperature"),
            "text": input_dict.get("text"),
            "tool_choice": input_dict.get("tool_choice"),
            "tools": input_dict.get("tools"),
            "top_p": input_dict.get("top_p"),
            "truncation": input_dict.get("truncation"),
            "user": input_dict.get("user"),
        },
        (
            response_create_params.ResponseCreateParamsStreaming
            if input_dict.get("stream")
            else response_create_params.ResponseCreateParamsNonStreaming
        ),
    )
    return json.dumps(json_dict), []


def _func_kwargs_to_json_str_openai_chat_completions_create(
    input_dict: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """Serialize OpenAI chat completions input to JSON string.

    Returns:
        Tuple of (json_str, attachments):
        - json_str: JSON representation of the input
        - attachments: List of attachment file IDs referenced in messages
    """
    from openai._utils._transform import maybe_transform
    from openai.types.chat import completion_create_params

    json_dict = maybe_transform(
        {
            "messages": input_dict.get("messages"),
            "model": input_dict.get("model"),
            "audio": input_dict.get("audio"),
            "frequency_penalty": input_dict.get("frequency_penalty"),
            "function_call": input_dict.get("function_call"),
            "functions": input_dict.get("functions"),
            "logit_bias": input_dict.get("logit_bias"),
            "logprobs": input_dict.get("logprobs"),
            "max_completion_tokens": input_dict.get("max_completion_tokens"),
            "max_tokens": input_dict.get("max_tokens"),
            "metadata": input_dict.get("metadata"),
            "modalities": input_dict.get("modalities"),
            "n": input_dict.get("n"),
            "parallel_tool_calls": input_dict.get("parallel_tool_calls"),
            "prediction": input_dict.get("prediction"),
            "presence_penalty": input_dict.get("presence_penalty"),
            "reasoning_effort": input_dict.get("reasoning_effort"),
            "response_format": input_dict.get("response_format"),
            "seed": input_dict.get("seed"),
            "service_tier": input_dict.get("service_tier"),
            "stop": input_dict.get("stop"),
            "store": input_dict.get("store"),
            "stream": input_dict.get("stream"),
            "stream_options": input_dict.get("stream_options"),
            "temperature": input_dict.get("temperature"),
            "tool_choice": input_dict.get("tool_choice"),
            "tools": input_dict.get("tools"),
            "top_logprobs": input_dict.get("top_logprobs"),
            "top_p": input_dict.get("top_p"),
            "user": input_dict.get("user"),
            "web_search_options": input_dict.get("web_search_options"),
        },
        (
            completion_create_params.CompletionCreateParamsStreaming
            if input_dict.get("stream")
            else completion_create_params.CompletionCreateParamsNonStreaming
        ),
    )
    return json.dumps(json_dict), []


def func_kwargs_to_json_str_openai(input_dict: Dict[str, Any], api_type: str):
    if api_type in ["OpenAI.chat.completions.create", "AsyncOpenAI.chat.completions.create"]:
        return _func_kwargs_to_json_str_openai_chat_completions_create(input_dict)
    elif api_type in ["OpenAI.responses.create", "AsyncOpenAI.responses.create"]:
        return _func_kwargs_to_json_str_openai_responses_create(input_dict)
    else:
        raise TypeError(f"Unknown API type {api_type}")


def api_obj_to_json_str_openai(obj: Any) -> str:
    return json.dumps(obj.to_dict(mode="json"))


def json_str_to_api_obj_openai(new_output_text: str, api_type: str) -> None:
    from openai._models import construct_type
    from openai.types.chat import ChatCompletion
    from openai.types.responses import Response

    if api_type in ["OpenAI.chat.completions.create", "AsyncOpenAI.chat.completions.create"]:
        type_ = ChatCompletion
    elif api_type in ["OpenAI.responses.create", "AsyncOpenAI.responses.create"]:
        type_ = Response
    else:
        raise TypeError(f"Unknown API type {api_type}")

    output_dict = json.loads(new_output_text)
    output_obj = construct_type(value=output_dict, type_=type_)
    return output_obj


def get_model_openai(input_dict: Dict[str, Any]) -> str:
    return input_dict.get("model", "unknown")
