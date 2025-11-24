from functools import wraps
from aco.runner.monkey_patching.patching_utils import get_input_dict, send_graph_node_and_edges
from aco.server.cache_manager import CACHE
from aco.common.logger import logger
from aco.runner.taint_wrappers import get_taint_origins, taint_wrap


def google_genai_patch():
    """
    Patch Vertex AI API to use persistent cache and edits.
    """
    try:
        from google import genai
    except ImportError:
        logger.info("Google GenAI not installed, skipping Vertex AI patches")
        return

    # Patch the Client.__init__ method to patch the models.generate_content method
    original_init = genai.Client.__init__

    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        patch_client_api_client_request(self.models._api_client)
        patch_client_api_client_async_request(self.models._api_client)

    genai.Client.__init__ = new_init


def patch_client_api_client_request(_api_client_instance):
    try:
        from google.genai._api_client import BaseApiClient
    except ImportError:
        return

    original_function = _api_client_instance.request

    @wraps(original_function)
    def patched_function(self, *args, **kwargs):
        api_type = "google.genai.models._api_client.request"

        # 2. Get full input dict.
        input_dict = get_input_dict(original_function, *args, **kwargs)

        # 3. Get taint origins (did another LLM produce the input?).
        taint_origins = get_taint_origins(input_dict)

        if not "generateContent" in input_dict.get("path"):
            # Just skip this if we are not generating content
            result = original_function(*args, **kwargs)
            return taint_wrap(result, taint_origins)

        # 4. Get result from cache or call LLM.
        cache_output = CACHE.get_in_out(input_dict, api_type)
        if cache_output.output is None:
            result = original_function(**cache_output.input_dict)  # Call LLM.
            CACHE.cache_output(cache_result=cache_output, output_obj=result, api_type=api_type)

        # 5. Tell server that this LLM call happened.
        send_graph_node_and_edges(
            node_id=cache_output.node_id,
            input_dict=cache_output.input_dict,
            output_obj=cache_output.output,
            source_node_ids=taint_origins,
            api_type=api_type,
        )

        # 6. Taint the output object and return it.
        return taint_wrap(cache_output.output, [cache_output.node_id])

    _api_client_instance.request = patched_function.__get__(_api_client_instance, BaseApiClient)


def patch_client_api_client_async_request(_api_client_instance):
    try:
        from google.genai._api_client import BaseApiClient
    except ImportError:
        return

    original_function = _api_client_instance.async_request

    @wraps(original_function)
    async def patched_function(self, *args, **kwargs):
        api_type = "google.genai.models._api_client.request"

        # 2. Get full input dict.
        input_dict = get_input_dict(original_function, *args, **kwargs)

        # 3. Get taint origins (did another LLM produce the input?).
        taint_origins = get_taint_origins(input_dict)

        if not "generateContent" in input_dict.get("path"):
            # Just skip this if we are not generating content
            result = await original_function(*args, **kwargs)
            return taint_wrap(result, taint_origins)

        # 4. Get result from cache or call LLM.
        cache_output = CACHE.get_in_out(input_dict, api_type)
        if cache_output.output is None:
            result = await original_function(**cache_output.input_dict)  # Call LLM.
            CACHE.cache_output(cache_result=cache_output, output_obj=result, api_type=api_type)

        # 5. Tell server that this LLM call happened.
        send_graph_node_and_edges(
            node_id=cache_output.node_id,
            input_dict=cache_output.input_dict,
            output_obj=cache_output.output,
            source_node_ids=taint_origins,
            api_type=api_type,
        )

        # 6. Taint the output object and return it.
        return taint_wrap(cache_output.output, [cache_output.node_id])

    _api_client_instance.async_request = patched_function.__get__(
        _api_client_instance, BaseApiClient
    )
