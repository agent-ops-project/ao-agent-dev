import time

from aco.common.constants import CERTAINTY_YELLOW
from aco.common.utils import send_to_server
from aco.runner.context_manager import get_session_id


def patched_call(input, output, input_ids, node_id, name, timeout, border_color=CERTAINTY_YELLOW):
    time.sleep(timeout)

    # Send node
    node_msg = {
        "type": "add_node",
        "session_id": get_session_id(),
        "node": {
            "id": node_id,
            "input": input,
            "output": output,
            "border_color": border_color,  # TODO: Set based on certainty.
            "label": name,  # TODO: Later label with LLM.
            "codeLocation": 0,
            "model": "gpt-3.5",
            "attachments": [],
        },
        "incoming_edges": input_ids,
    }

    try:
        send_to_server(node_msg)
    except Exception as e:
        pass
