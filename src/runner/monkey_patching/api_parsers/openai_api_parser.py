import json
from typing import Any, Dict, List, Tuple


def _get_input_openai_responses_create(
    input_dict: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """Extract input text and attachments from OpenAI responses create input."""
    from openai._utils._transform import maybe_transform
    from openai.types.responses import response_create_params

    json_dict = maybe_transform(
        input_dict,
        (
            response_create_params.ResponseCreateParamsStreaming
            if input_dict["stream"]
            else response_create_params.ResponseCreateParamsNonStreaming
        ),
    )
    return json.dumps(json_dict), []


def _get_input_openai_chat_completions_create(
    input_dict: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """Serialize OpenAI chat completions input to JSON string.

    Returns:
        Tuple of (json_str, attachments):
        - json_str: JSON representation of the input
        - attachments: List of attachment file IDs referenced in messages
    """
    from openai._utils._transform import maybe_transform
    from openai.types.responses import response_create_params

    json_dict = maybe_transform(
        input_dict,
        (
            response_create_params.ResponseCreateParamsStreaming
            if input_dict["stream"]
            else response_create_params.ResponseCreateParamsNonStreaming
        ),
    )
    return json.dumps(json_dict), []


def _get_output_openai(obj: Any) -> str:
    return json.dumps(obj.to_dict(mode="json"))


def _set_input_openai(original_input_dict: Dict[str, Any], new_input_text: str) -> None:
    original_input_dict["input"] = json.loads(new_input_text)
    return original_input_dict


def _set_output_openai(original_output_obj: Any, output_text: str) -> None:
    from openai._models import construct_type

    out_out_dict = json.loads(output_text)
    output_obj = construct_type(value=out_out_dict, type_=type(original_output_obj))
    return output_obj


def _get_model_openai(input_dict: Dict[str, Any]) -> str:
    return input_dict.get("model", "unknown")
