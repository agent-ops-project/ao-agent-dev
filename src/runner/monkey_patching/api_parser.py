import json
from typing import Any, Dict, List, Tuple
from aco.runner.monkey_patching.api_parsers.mcp_api_parser import (
    func_kwargs_to_json_str_mcp,
    api_obj_to_json_str_mcp,
    json_str_to_api_obj_mcp,
    json_str_to_original_inp_dict_mcp,
    get_model_mcp,
)
from aco.runner.monkey_patching.api_parsers.httpx_api_parser import (
    func_kwargs_to_json_str_httpx,
    api_obj_to_json_str_httpx,
    json_str_to_api_obj_httpx,
    json_str_to_original_inp_dict_httpx,
    get_model_httpx,
)
from aco.runner.monkey_patching.api_parsers.requests_api_parser import (
    func_kwargs_to_json_str_requests,
    api_obj_to_json_str_requests,
    json_str_to_api_obj_requests,
    json_str_to_original_inp_dict_requests,
    get_model_requests,
)


def json_str_to_original_inp_dict(json_str: str, input_dict: dict, api_type: str) -> dict:
    if api_type == "requests.Session.send":
        return json_str_to_original_inp_dict_requests(json_str, input_dict)
    elif api_type in ["httpx.Client.send", "httpx.AsyncClient.send"]:
        return json_str_to_original_inp_dict_httpx(json_str, input_dict)
    elif api_type == "MCP.ClientSession.send_request":
        return json_str_to_original_inp_dict_mcp(json_str, input_dict)
    else:
        return json.loads(json_str)


def func_kwargs_to_json_str(input_dict: Dict[str, Any], api_type: str) -> Tuple[str, List[str]]:
    if api_type == "requests.Session.send":
        return func_kwargs_to_json_str_requests(input_dict)
    elif api_type in ["httpx.Client.send", "httpx.AsyncClient.send"]:
        return func_kwargs_to_json_str_httpx(input_dict)
    elif api_type == "MCP.ClientSession.send_request":
        return func_kwargs_to_json_str_mcp(input_dict)
    else:
        raise ValueError(f"Unknown API type {api_type}")


def api_obj_to_response_ok(response_obj: Any, api_type: str) -> bool:
    if api_type == "requests.Session.send":
        return response_obj.ok
    elif api_type in ["httpx.Client.send", "httpx.AsyncClient.send"]:
        return response_obj.is_success
    else:
        return True


def api_obj_to_json_str(response_obj: Any, api_type: str) -> str:
    if api_type == "requests.Session.send":
        return api_obj_to_json_str_requests(response_obj)
    elif api_type in ["httpx.Client.send", "httpx.AsyncClient.send"]:
        return api_obj_to_json_str_httpx(response_obj)
    elif api_type == "MCP.ClientSession.send_request":
        return api_obj_to_json_str_mcp(response_obj)
    else:
        raise ValueError(f"Unknown API type {api_type}")


def json_str_to_api_obj(new_output_text: str, api_type: str) -> Any:
    if api_type == "requests.Session.send":
        return json_str_to_api_obj_requests(new_output_text)
    elif api_type in ["httpx.Client.send", "httpx.AsyncClient.send"]:
        return json_str_to_api_obj_httpx(new_output_text)
    elif api_type == "MCP.ClientSession.send_request":
        return json_str_to_api_obj_mcp(new_output_text)
    else:
        raise ValueError(f"Unknown API type {api_type}")


def get_model_name(input_dict: Dict[str, Any], api_type: str) -> str:
    if api_type == "requests.Session.send":
        return get_model_requests(input_dict)
    elif api_type in ["httpx.Client.send", "httpx.AsyncClient.send"]:
        return get_model_httpx(input_dict)
    elif api_type == "MCP.ClientSession.send_request":
        return get_model_mcp(input_dict)
    else:
        raise ValueError(f"Unknown API type {api_type}")
