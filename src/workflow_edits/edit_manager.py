from common.logging_config import setup_logging
from . import db
import json
from openai.types.responses.response import Response
logger = setup_logging()


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
        logger.debug(f"set_input_overwrite called: session_id={session_id}, model={model}, input={repr(input)}, new_input={repr(new_input)}")
        input_hash = db.hash_input(input)
        new_input_hash = db.hash_input(new_input)
        logger.debug(f"input_hash={input_hash}, new_input_hash={new_input_hash}")
        
        # Check if a row with (session_id, model, input_overwrite_hash) exists
        existing_overwrite_row = db.query_one(
            "SELECT * FROM nodes WHERE session_id=? AND model=? AND input_overwrite_hash=?",
            (session_id, model, input_hash)
        )
        logger.debug(f"existing_overwrite_row: {existing_overwrite_row}")
        
        if existing_overwrite_row:
            # Case 1: Server sent overwritten input.
            logger.debug(f"Case 1: Updating existing overwrite row")
            db.execute(
                "UPDATE nodes SET input_overwrite=?, input_overwrite_hash=?, output=NULL WHERE session_id=? AND model=? AND input_overwrite_hash=?",
                (new_input, new_input_hash, session_id, model, input_hash)
            )
        else:
            # Case 2: Server sent original input.
            logger.debug(f"Case 2: Updating original input row")
            db.execute(
                "UPDATE nodes SET input_overwrite=?, input_overwrite_hash=?, output=NULL WHERE session_id=? AND model=? AND input_hash=?",
                (new_input, new_input_hash, session_id, model, input_hash)
            )

    def set_output_overwrite(self, session_id, model, input, new_output, api_type=None):
        logger.debug(f"set_output_overwrite called: session_id={session_id}, model={model}, input={repr(input)}, new_output={repr(new_output)}, api_type={api_type}")
        input_hash = db.hash_input(input)
        logger.debug(f"input_hash={input_hash}")
        
        # Get the original output from the database
        row = db.query_one(
            "SELECT output, api_type FROM nodes WHERE session_id=? AND model=? AND input_hash=?",
            (session_id, model, input_hash)
        )
        logger.debug(f"Found row: {row}")
        
        if not row or not row["output"]:
            # No original output found, can't create edited version
            logger.debug(f"No original output found, returning")
            return
        
        original_output = row["output"]
        api_type = api_type or row["api_type"]
        logger.debug(f"original_output={repr(original_output)}, api_type={api_type}")
        
        # Create updated output by swapping the text
        from .utils import swap_output
        updated_output = swap_output(new_output, original_output, api_type)
        logger.debug(f"updated_output={repr(updated_output)}")
        
        # Check if a row with (session_id, model, input_overwrite_hash) exists
        existing_overwrite_row = db.query_one(
            "SELECT * FROM nodes WHERE session_id=? AND model=? AND input_overwrite_hash=?",
            (session_id, model, input_hash)
        )
        
        if existing_overwrite_row:
            # Case 1: Server sent overwritten input.
            db.execute(
                "UPDATE nodes SET output=? WHERE session_id=? AND model=? AND input_overwrite_hash=?",
                (updated_output, session_id, model, input_hash)
            )
        else:
            # Case 2: Server passed original input.
            db.execute(
                "UPDATE nodes SET output=? WHERE session_id=? AND model=? AND input_hash=?",
                (updated_output, session_id, model, input_hash)
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