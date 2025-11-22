import json
from typing import Any, Dict, List, Tuple


def func_kwargs_to_json_str_anthropic(
    input_dict: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """Serialize Anthropic create messages input to JSON string.

    Returns:
        Tuple of (json_str, attachments):
        - json_str: JSON representation of the input
        - attachments: List of attachment file IDs referenced in messages
    """
    from anthropic._utils._transform import maybe_transform
    from anthropic.types import message_create_params

    json_dict = maybe_transform(
        {
            "max_tokens": input_dict.get("max_tokens"),
            "messages": input_dict.get("messages"),
            "model": input_dict.get("model"),
            "metadata": input_dict.get("metadata"),
            "service_tier": input_dict.get("service_tier"),
            "stop_sequences": input_dict.get("stop_sequences"),
            "stream": input_dict.get("stream"),
            "system": input_dict.get("system"),
            "temperature": input_dict.get("temperature"),
            "thinking": input_dict.get("thinking"),
            "tool_choice": input_dict.get("tool_choice"),
            "tools": input_dict.get("tools"),
            "top_k": input_dict.get("top_k"),
            "top_p": input_dict.get("top_p"),
        },
        (
            message_create_params.MessageCreateParamsStreaming
            if input_dict.get("stream")
            else message_create_params.MessageCreateParamsNonStreaming
        ),
    )
    return json.dumps(json_dict), []


def api_obj_to_json_str_anthropic(obj: Any) -> str:
    return json.dumps(obj.to_dict(mode="json"))


def json_str_to_api_obj_anthropic(new_output_text: str) -> None:
    from anthropic._models import construct_type
    from anthropic.types.message import Message

    output_dict = json.loads(new_output_text)
    output_obj = construct_type(value=output_dict, type_=Message)
    return output_obj


def get_model_anthropic(input_dict: Dict[str, Any]) -> str:
    return input_dict.get("model", "unknown")
