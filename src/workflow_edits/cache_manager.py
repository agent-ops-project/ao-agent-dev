import hashlib
import pickle
import yaml
import uuid

from runtime_tracing.taint_wrappers import untaint_if_needed
from workflow_edits.utils import  response_to_json
from workflow_edits import db


def cache_key(fn, args, kwargs):
    context = {
        "fn": fn.__module__ + '.' + fn.__qualname__,
        "args": args,
        "kwargs": kwargs,
    }
    raw = pickle.dumps(context)
    return raw


class CacheManager:
    """
    Handles persistent caching and retrieval of LLM call inputs/outputs per experiment session.
    Uses the llm_calls table in the workflow edits database.
    """

    def get_in_out(self, session_id, model, input):
        input = untaint_if_needed(input)
        input_hash = db.hash_input(input)
        row = db.query_one(
            "SELECT input, input_overwrite, output, node_id FROM llm_calls WHERE session_id=? AND model=? AND input_hash=?",
            (session_id, model, input_hash)
        )

        if row is None:
            # Insert new row with a new node_id
            node_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO llm_calls (session_id, model, input, input_hash, node_id) VALUES (?, ?, ?, ?, ?)",
                (session_id, model, input, input_hash, node_id)
            )
            return input, None, node_id

        input_val = row["input"]
        assert input_val is not None
        input_overwrite_val = row["input_overwrite"]
        output = row["output"]
        node_id = row["node_id"]

        # Get input_to_use
        if input_overwrite_val is not None:
            input_to_use = input_overwrite_val
        else:
            input_to_use = input_val

        return input_to_use, output, node_id

    def cache_output(self, session_id, model, input, output, api_type, node_id):
        input_hash = db.hash_input(input)
        # Serialize Response object to JSON
        output_to_store = response_to_json(output, api_type)
        
        if node_id:
            db.execute(
                "UPDATE llm_calls SET output=?, api_type=?, node_id=? WHERE session_id=? AND model=? AND input_hash=?",
                (output_to_store, api_type, node_id, session_id, model, input_hash)
            )
        else:
            db.execute(
                "UPDATE llm_calls SET output=?, api_type=? WHERE session_id=? AND model=? AND input_hash=?",
                (output_to_store, api_type, session_id, model, input_hash)
            )


CACHE = CacheManager()
