from . import db
import json
from openai.types.responses.response import Response

class EditManager:
    """
    Handles user edits to LLM call inputs and outputs, updating the persistent database.
    """
    @staticmethod
    def inject_output_text(response_dict: dict, new_text: str) -> dict:
        """Inject new_text into the correct place in the response dict."""
        try:
            response_dict["output"][0]["content"][0]["text"] = new_text
        except Exception as e:
            raise ValueError(f"Failed to inject output text: {e}")
        return response_dict

    def set_input_overwrite(self, session_id, model, input, new_input):
        input_hash = db.hash_input(input)
        db.execute(
            "UPDATE nodes SET input_overwrite=? WHERE session_id=? AND model=? AND input_hash=?",
            (new_input, session_id, model, input_hash)
        )

    def set_output_overwrite(self, session_id, model, input, new_output, api_type=None):
        input_hash = db.hash_input(input)
        row = db.query_one(
            "SELECT output FROM nodes WHERE session_id=? AND model=? AND input_hash=?",
            (session_id, model, input_hash)
        )
        if row and row["output"]:
            if api_type == "openai_v2":
                response_dict = json.loads(row["output"])
                response_dict = self.inject_output_text(response_dict, new_output)
                updated_json = json.dumps(response_dict)
            else:
                updated_json = new_output
            db.execute(
                "UPDATE nodes SET output=? WHERE session_id=? AND model=? AND input_hash=?",
                (updated_json, session_id, model, input_hash)
            )

    def remove_input_overwrite(self, session_id, node_id):
        db.execute(
            "UPDATE nodes SET input_overwrite=NULL WHERE session_id=? AND node_id=?",
            (session_id, node_id)
        )

    def remove_output_overwrite(self, session_id, node_id):
        db.execute(
            "UPDATE nodes SET output=NULL WHERE session_id=? AND node_id=?",
            (session_id, node_id)
        )

EDIT = EditManager() 