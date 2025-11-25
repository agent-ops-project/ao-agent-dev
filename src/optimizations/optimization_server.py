"""
Optimization server for handling graph optimization requests.

This server connects to the develop server as a client and handles
optimization-related operations like similarity search.
"""

import socket
import json
import time
from typing import Optional
from aco.common.logger import logger
from aco.common.constants import HOST, PORT


def send_json(conn: socket.socket, msg: dict) -> None:
    """Send a JSON message over a socket connection."""
    try:
        msg_type = msg.get("type", "unknown")
        logger.debug(f"[OptimizationServer] Sent message type: {msg_type}")
        conn.sendall((json.dumps(msg) + "\n").encode("utf-8"))
    except Exception as e:
        logger.error(f"[OptimizationServer] Error sending JSON: {e}")


class OptimizationClient:
    """
    Optimization client that connects to the develop server.
    
    This client handles optimization requests from the develop server,
    processing operations like similarity search, clustering, and 
    graph transformations.
    """
    
    def __init__(self):
        self.conn: Optional[socket.socket] = None
        self.running = True
        
    # ============================================================
    # Message Handlers
    # ============================================================
    
    def handle_add_node(self, msg: dict) -> None:
        """
        Given (session_id, node_id, input_str), compute input_str embedding and 
        add to DB. 
        """
        session_id = msg.get("session_id")
        node_id = msg.get("node_id")
        input_str = msg.get("input_str") # embed this string

        # TODO(Mahit): Store in DB |session_id | node_id | input_str |


    def handle_similarity_search(self, msg: dict) -> None:
        """
        Given (session_id, node_id) return the k most similar [(session_id, node_id)]. 
        """
        session_id = msg.get("session_id") # compute sim to this session_id
        node_id = msg.get("node_id") # compute sim to this node_id
        top_k = msg.get("k") # fetch so many other [(session_id, node_id)]

        # TODO(Mahit): Let's implement a first, dummy approach here:
        # 1. Get input from lesson_embeddings table (given session_id and node_id)
        # 2. Compute the top-k session_ids and node_ids with the most similar input embeddings. Exluding the one given as input here.
        # 3. Return the list of session_ids and node_ids.

        logger.debug(f"[OptimizationServer] Similarity search for session {session_id}, node {node_id}")
        
        # TODO: Fill in placeholder below
        response = {
            "type": "similarity_runs",
            "session_id": session_id,
            "results": []
        }
        
        send_json(self.conn, response)
    

    def handle_shutdown(self, msg: dict) -> None:
        """Handle shutdown command from develop server."""
        logger.info("[OptimizationServer] Shutdown command received")
        self.running = False
    
    # ============================================================
    # Message Routing
    # ============================================================
    
    def process_message(self, msg: dict) -> None:
        """
        Route messages to appropriate handlers based on message type.
        
        Args:
            msg: The message dictionary with a 'type' field
        """
        msg_type = msg.get("type", "unknown")
        logger.debug(f"[OptimizationServer] Processing message type: {msg_type}")
        
        handlers = {
            "similarity_search": self.handle_similarity_search,
            "cluster_nodes": self.handle_cluster_nodes,
            "optimize_graph": self.handle_optimize_graph,
            "shutdown": self.handle_shutdown,
        }
        
        handler = handlers.get(msg_type)
        if handler:
            handler(msg)
        else:
            logger.warning(f"[OptimizationServer] Unknown message type: {msg_type}")
    
    def connect_to_develop_server(self) -> bool:
        """
        Connect to the develop server as an optimization client.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.conn = socket.create_connection((HOST, PORT), timeout=5)
            
            # Send handshake identifying as optimization role
            handshake = {
                "type": "handshake",
                "role": "optimization"
            }
            send_json(self.conn, handshake)
            
            # Wait for session_id acknowledgment
            file_obj = self.conn.makefile("r")
            response_line = file_obj.readline()
            if response_line:
                response = json.loads(response_line.strip())
                if response.get("type") == "session_id":
                    logger.info("[OptimizationServer] Connected to develop server")
                    return True
                else:
                    logger.error(f"[OptimizationServer] Unexpected handshake response: {response}")
                    
        except Exception as e:
            logger.error(f"[OptimizationServer] Failed to connect to develop server: {e}")
            
        return False
    
    def run(self) -> None:
        """
        Main loop: connect to develop server and process messages.
        """
        # Retry connection with backoff
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries and self.running:
            if self.connect_to_develop_server():
                break
            retry_count += 1
            wait_time = min(2 ** retry_count, 30)  # Exponential backoff, max 30 seconds
            logger.info(f"[OptimizationServer] Retrying connection in {wait_time} seconds...")
            time.sleep(wait_time)
        
        if not self.conn:
            logger.error("[OptimizationServer] Failed to connect after retries")
            return
        
        file_obj = self.conn.makefile("r")
        
        try:
            # Main message processing loop
            for line in file_obj:
                if not self.running:
                    break
                    
                try:
                    msg = json.loads(line.strip())
                    self.process_message(msg)
                except json.JSONDecodeError as e:
                    logger.error(f"[OptimizationServer] Error parsing JSON: {e}")
                except Exception as e:
                    logger.error(f"[OptimizationServer] Error processing message: {e}")
                    
        except Exception as e:
            logger.error(f"[OptimizationServer] Connection error: {e}")
        finally:
            if self.conn:
                try:
                    self.conn.close()
                except:
                    pass
            logger.info("[OptimizationServer] Disconnected from develop server")


def main():
    """Main entry point for the optimization server."""
    client = OptimizationClient()
    try:
        client.run()
    except KeyboardInterrupt:
        logger.info("[OptimizationServer] Interrupted by user")
    except Exception as e:
        logger.error(f"[OptimizationServer] Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()