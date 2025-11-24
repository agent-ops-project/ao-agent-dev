import json
from typing import Any, Dict, List, Tuple


def func_kwargs_to_json_str_google(
    input_dict: Dict[str, Any],
) -> Tuple[str, List[str]]:
    return json.dumps(input_dict), []


def api_obj_to_json_str_google(obj: Any) -> str:
    body_json = json.loads(obj.body)
    complete_json = {"headers": obj.headers, "body": body_json}
    return json.dumps(complete_json)


def json_str_to_api_obj_google(new_output_text: str) -> None:
    from google.genai.types import HttpResponse

    json_dict = json.loads(new_output_text)
    return HttpResponse(headers=json_dict["headers"], body=json.dumps(json_dict["body"]))


def get_model_google(input_dict: Dict[str, Any]) -> str:
    try:
        return input_dict["request_dict"]["_url"]["model"]
    except Exception:
        pass

    try:
        path = input_dict["path"]
        if ":" in path:
            return path.split(":")[-2]
        return path
    except Exception:
        return "undefined"
