from workflow_edits import db
import json
from openai.types.responses.response import Response
from workflow_edits.utils import swap_output

class EditManager:
    """
    Handles user edits to LLM call inputs and outputs, updating the persistent database.
    Uses the llm_calls table in the workflow edits database.
    """
    @staticmethod
    def inject_output_text(response_dict: dict, new_text: str) -> dict:
        """Inject new_text into the correct place in the response dict."""
        try:
            response_dict["output"][0]["content"][0]["text"] = new_text
        except Exception as e:
            raise ValueError(f"Failed to inject output text: {e}")
        return response_dict

    # def set_input_overwrite(self, session_id, model, input, new_input):
    #     input_hash = db.hash_input(input)
    #     new_input_hash = db.hash_input(new_input)
        
    #     # Check if a row with (session_id, model, input_overwrite_hash) exists
    #     existing_overwrite_row = db.query_one(
    #         "SELECT * FROM llm_calls WHERE session_id=? AND model=? AND input_overwrite_hash=?",
    #         (session_id, model, input_hash)
    #     )
        
    #     if existing_overwrite_row:
    #         # Case 1: Server sent overwritten input.
    #         db.execute(
    #             "UPDATE llm_calls SET input_overwrite=?, input_overwrite_hash=?, output=NULL WHERE session_id=? AND model=? AND input_overwrite_hash=?",
    #             (new_input, new_input_hash, session_id, model, input_hash)
    #         )
    #     else:
    #         # Case 2: Server sent original input.
    #         db.execute(
    #             "UPDATE llm_calls SET input_overwrite=?, input_overwrite_hash=?, output=NULL WHERE session_id=? AND model=? AND input_hash=?",
    #             (new_input, new_input_hash, session_id, model, input_hash)
    #         )


    def set_input_overwrite(self, session_id, node_id, new_input):
        new_input_hash = db.hash_input(new_input)
        db.execute(
            "UPDATE llm_calls SET input_overwrite=?, input_overwrite_hash=?, output=NULL WHERE session_id=? AND node_id=?",
            (new_input, new_input_hash, session_id, node_id)
        )


    def set_output_overwrite(self, session_id, node_id, new_output):
        # Get api_type and output for the given session_id and node_id
        row = db.query_one(
            "SELECT api_type, output FROM llm_calls WHERE session_id=? AND node_id=?",
            (session_id, node_id)
        )
        if not row or row["output"] is None:
            raise ValueError(f"No output found for session_id={session_id}, node_id={node_id}")
        api_type = row["api_type"]
        existing_output = row["output"]
        updated_output_json = swap_output(new_output, existing_output, api_type)
        db.execute(
            "UPDATE llm_calls SET output=? WHERE session_id=? AND node_id=?",
            (updated_output_json, session_id, node_id)
        )


    # def set_output_overwrite(self, session_id, model, input, new_output, api_type):
    #     input_hash = db.hash_input(input)

    #     # Case 1: Server passed overwritten input
    #     existing_overwrite_row = db.query_one(
    #         "SELECT output FROM llm_calls WHERE session_id=? AND model=? AND input_overwrite_hash=?",
    #         (session_id, model, input_hash)
    #     )

    #     if existing_overwrite_row and existing_overwrite_row["output"] is not None:
    #         # Creat output json and update DB
    #         updated_output_json = swap_output(new_output, existing_overwrite_row["output"], api_type)
    #         db.execute(
    #             "UPDATE llm_calls SET output=? WHERE session_id=? AND model=? AND input_overwrite_hash=?",
    #             (updated_output_json, session_id, model, input_hash)
    #         )
    #         return

    #     # Case 2: Server passed original input.
    #     existing_row = db.query_one(
    #         "SELECT output FROM llm_calls WHERE session_id=? AND model=? AND input_hash=?",
    #         (session_id, model, input_hash)
    #     )

    #     assert existing_row and existing_row["output"] is not None
    #     updated_output_json = swap_output(new_output, existing_row["output"], api_type)
    #     db.execute(
    #         "UPDATE llm_calls SET output=? WHERE session_id=? AND model=? AND input_hash=?",
    #         (updated_output_json, session_id, model, input_hash)
    #     )

    def remove_input_overwrite(self, session_id, node_id):
        db.execute(
            "UPDATE llm_calls SET input_overwrite=NULL WHERE session_id=? AND node_id=?",
            (session_id, node_id)
        )

    def remove_output_overwrite(self, session_id, node_id):
        db.execute(
            "UPDATE llm_calls SET output=NULL WHERE session_id=? AND node_id=?",
            (session_id, node_id)
        )

    def add_experiment(self, session_id, timestamp, cwd, command):
        default_graph = json.dumps({"nodes": [], "edges": []})
        db.execute(
            "INSERT INTO experiments (session_id, graph_topology, timestamp, cwd, command) VALUES (?, ?, ?, ?, ?)",
            (session_id, default_graph, timestamp, cwd, command)
        )

    def update_graph_topology(self, session_id, graph_dict):
        import json
        graph_json = json.dumps(graph_dict)
        db.execute(
            "UPDATE experiments SET graph_topology=? WHERE session_id=?",
            (graph_json, session_id)
        )

EDIT = EditManager() 