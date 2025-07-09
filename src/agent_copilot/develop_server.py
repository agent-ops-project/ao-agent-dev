import socket
import sys
import os
import argparse
import json
import threading
import subprocess
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, Set, Tuple

# Configuration constants
HOST = '127.0.0.1'
PORT = 5959
SOCKET_TIMEOUT = 3
SHUTDOWN_WAIT = 2

class Session:
    """Represents a running develop process and its associated UI clients."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.shim_conn: Optional[socket.socket] = None
        self.lock = threading.Lock()

class DevelopServer:
    """Manages the development server for LLM call visualization."""
    
    def __init__(self):
        self.server_sock = None
        self.lock = threading.Lock()
        self.conn_info = {}  # conn -> {role, session_id, process_id}
        self.process_info = {}  # process_id -> info
        self.dashim_pid_map = {}  # process_id -> (session_id, conn)
        self.session_graphs = {}  # session_id -> graph_data
        self.ui_connections = set()  # All UI connections (simplified)
        self.sessions = {}  # session_id -> Session (only for shim connections)
    
    def send_json(self, conn: socket.socket, msg: dict) -> None:
        try:
            conn.sendall((json.dumps(msg) + "\n").encode("utf-8"))
        except Exception as e:
            print(f"[develop_server] Error sending JSON: {e}")
    
    def broadcast_to_all_uis(self, msg: dict) -> None:
        """Broadcast a message to all UI connections."""
        for ui_conn in list(self.ui_connections):
            try:
                self.send_json(ui_conn, msg)
            except Exception as e:
                print(f"[develop_server] Error broadcasting to UI: {e}")
                self.ui_connections.discard(ui_conn)
    
    def broadcast_experiment_list_to_all_uis(self) -> None:
        experiment_list = [
            {
                "session_id": info.get("session_id", ""),
                "status": info.get("status", "running"),
                "timestamp": info.get("timestamp", "")
            }
            for pid, info in self.process_info.items() if info.get("role") == "shim-control"
        ]
        msg = {"type": "experiment_list", "experiments": experiment_list}
        self.broadcast_to_all_uis(msg)
    
    def route_message(self, sender: socket.socket, msg: dict) -> None:
        """Route a message based on sender role."""
        info = self.conn_info.get(sender)
        if not info:
            return
        role = info["role"]
        session_id = info["session_id"]
        session = self.sessions.get(session_id)
        if not session:
            return
        
        # Route based on sender role
        if role == "ui":
            # UI → Shim
            if session.shim_conn:
                self.send_json(session.shim_conn, msg)
        elif role == "shim":
            # Shim → all UIs
            self.broadcast_to_all_uis(msg)
    
    def handle_shutdown(self) -> None:
        """Handle shutdown command by closing all connections."""
        print("[develop_server] Shutdown command received. Closing all connections.")
        # Close all client sockets
        for s in list(self.conn_info.keys()):
            print(f"Closing socket: {s}")
            try:
                s.close()
            except Exception as e:
                print(f"Error closing socket: {e}")
        os._exit(0)
    
    def handle_restart_message(self, msg: dict) -> bool:
        """Handle restart message with process_id, route to correct shim."""
        if msg.get("type") == "restart" and "process_id" in msg:
            pid = msg["process_id"]
            target = self.dashim_pid_map.get(pid)
            if target:
                _, shim_conn = target
                self.send_json(shim_conn, msg)
                return True  # Message handled
        return False
    
    def handle_deregister_message(self, msg: dict) -> bool:
        if msg.get("type") == "deregister" and "process_id" in msg:
            pid = msg["process_id"]
            role = None
            for conn, info in list(self.conn_info.items()):
                if info.get("process_id") == pid:
                    role = info.get("role")
                    break
            if pid in self.dashim_pid_map:
                del self.dashim_pid_map[pid]
                self._mark_process_finished(role, pid)
                return True
        return False
    
    def handle_debugger_restart_message(self, msg: dict) -> bool:
        """Handle debugger restart notification, update session info."""
        if msg.get("type") == "debugger_restart" and "process_id" in msg:
            pid = msg["process_id"]
            if pid in self.dashim_pid_map:
                session_id, shim_conn = self.dashim_pid_map[pid]
                if session_id in self.sessions:
                    if pid in self.process_info:
                        self.broadcast_experiment_list_to_all_uis()
            return True
        return False
    
    def _track_process(self, role: str, process_id: int, session_id: str) -> None:
        if role == "shim-control":
            # Create timestamp in DD/MM HH:MM format
            timestamp = datetime.now().strftime("%d/%m %H:%M")
            self.process_info[process_id] = {
                "session_id": session_id,
                "status": "running",
                "role": role,
                "timestamp": timestamp
            }
            self.broadcast_experiment_list_to_all_uis()

    def _mark_process_finished(self, role: str, process_id: int) -> None:
        if role == "shim-control" and process_id in self.process_info:
            self.process_info[process_id]["status"] = "finished"
            self.broadcast_experiment_list_to_all_uis()
    
    def handle_client(self, conn: socket.socket) -> None:
        """Handle a new client connection in a separate thread."""
        file_obj = conn.makefile(mode='r')
        session: Optional[Session] = None
        process_id = None
        role = None
        
        try:
            # Expect handshake first
            handshake_line = file_obj.readline()
            if not handshake_line:
                return
            handshake = json.loads(handshake_line.strip())
            role = handshake.get("role")
            script = handshake.get("script")
            session_id = handshake.get("session_id")
            process_id = handshake.get("process_id")
            
            if not session_id:
                session_id = str(uuid.uuid4())
            
            with self.lock:
                if session_id not in self.sessions:
                    self.sessions[session_id] = Session(session_id)
                session = self.sessions[session_id]
            
            if role == "shim-control":
                with session.lock:
                    session.shim_conn = conn
                if process_id is not None:
                    self.dashim_pid_map[process_id] = (session_id, conn)
                    self._track_process(role, process_id, session_id)
            elif role == "ui":
                # Add UI to global connections list
                self.ui_connections.add(conn)
                self.broadcast_experiment_list_to_all_uis()
                
                # Send current graph data for all sessions to the new UI
                for sid, graph_data in self.session_graphs.items():
                    if graph_data.get("nodes") or graph_data.get("edges"):
                        self.send_json(conn, {
                            "type": "graph_update",
                            "session_id": sid,
                            "payload": graph_data
                        })
            
            self.conn_info[conn] = {"role": role, "session_id": session_id, "process_id": process_id}
            self.send_json(conn, {"type": "session_id", "session_id": session_id})
            
            # Main message loop
            try:
                for line in file_obj:
                    try:
                        msg = json.loads(line.strip())
                    except Exception as e:
                        print(f"[develop_server] Error parsing JSON: {e}")
                        continue
                    
                    # Print message type (with error handling)
                    try:
                        msg_type = msg.get("type", "unknown")
                        print(f"[develop_server] Received message type: {msg_type}")
                    except Exception:
                        pass  # Skip printing if there's a key error
                    
                    if "session_id" not in msg:
                        msg["session_id"] = session_id
                    
                    # Handle special message types
                    if msg.get("type") == "shutdown":
                        self.handle_shutdown()
                    elif self.handle_restart_message(msg):
                        continue  # Don't route to all shims
                    elif self.handle_deregister_message(msg):
                        continue
                    elif self.handle_debugger_restart_message(msg):
                        continue
                    elif msg.get("type") == "addNode":
                        sid = msg["session_id"]
                        node = msg["node"]
                        graph = self.session_graphs.setdefault(sid, {"nodes": [], "edges": []})
                        # Update or add node
                        for i, n in enumerate(graph["nodes"]):
                            if n["id"] == node["id"]:
                                graph["nodes"][i] = node
                                break
                        else:
                            graph["nodes"].append(node)
                        # Broadcast updated graph to all UIs
                        self.broadcast_to_all_uis({
                            "type": "graph_update",
                            "session_id": sid,
                            "payload": {"nodes": graph["nodes"], "edges": graph["edges"]}
                        })
                        continue
                    elif msg.get("type") == "addEdge":
                        sid = msg["session_id"]
                        edge = msg["edge"]
                        graph = self.session_graphs.setdefault(sid, {"nodes": [], "edges": []})
                        # Only add edge if not already present
                        if not any(e["source"] == edge["source"] and e["target"] == edge["target"] for e in graph["edges"]):
                            edge_id = f"e{edge['source']}-{edge['target']}"
                            edge_with_id = {"id": edge_id, **edge}
                            graph["edges"].append(edge_with_id)
                        # Broadcast updated graph to all UIs
                        self.broadcast_to_all_uis({
                            "type": "graph_update",
                            "session_id": sid,
                            "payload": {"nodes": graph["nodes"], "edges": graph["edges"]}
                        })
                        continue
                    else:
                        self.route_message(conn, msg)
                        
            except (ConnectionResetError, OSError) as e:
                print(f"[develop_server] Connection closed: {e}")
        finally:
            # Clean up connection
            info = self.conn_info.pop(conn, None)
            if info and session:
                if info["role"] == "shim":
                    with session.lock:
                        session.shim_conn = None
                    # Remove from pid map if present
                    for pid, (sess_id, c) in list(self.dashim_pid_map.items()):
                        if c == conn:
                            del self.dashim_pid_map[pid]
                            # Only remove from process info if shim-runner
                            self._mark_process_finished(info.get("role"), pid)
                elif info["role"] == "ui":
                    # Remove from global UI connections list
                    self.ui_connections.discard(conn)
            try:
                conn.close()
            except Exception as e:
                print(f"[develop_server] Error closing connection: {e}")
    
    def run_server(self) -> None:
        """Main server loop: accept clients and spawn handler threads."""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((HOST, PORT))
        self.server_sock.listen()
        print(f"Develop server listening on {HOST}:{PORT}")
        
        try:
            while True:
                conn, addr = self.server_sock.accept()
                threading.Thread(
                    target=self.handle_client, 
                    args=(conn,), 
                    daemon=True
                ).start()
        except OSError:
            # This will be triggered when server_sock is closed (on shutdown)
            pass
        finally:
            self.server_sock.close()
            print("Develop server stopped.")

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Development server for LLM call visualization")
    parser.add_argument('command', choices=['start', 'stop', 'restart'], 
                       help="Start or stop the server")
    args = parser.parse_args()

    if args.command == 'start':
        # If server is already running, do not start another
        try:
            socket.create_connection((HOST, PORT), timeout=1).close()
            print("Develop server is already running.")
            return
        except Exception:
            pass
        # Launch the server as a detached background process (POSIX)
        subprocess.Popen([sys.executable, __file__, "--serve"],
                        close_fds=True, start_new_session=True)
        print("Develop server started.")
        
    elif args.command == 'stop':
        # Connect to the server and send a shutdown command
        try:
            sock = socket.create_connection((HOST, PORT), timeout=SOCKET_TIMEOUT)
            # The server will only accept messages from this process after a handshake.
            handshake = {"type": "hello", "role": "ui", "script": "stopper"}
            sock.sendall((json.dumps(handshake) + "\n").encode('utf-8'))
            # Send shutdown message
            sock.sendall((json.dumps({"type": "shutdown"}) + "\n").encode('utf-8'))
            sock.close()
            print("Develop server stop signal sent.")
        except Exception:
            print("No running server found.")
            sys.exit(1)
            
    elif args.command == 'restart':
        # Stop the server if running
        try:
            sock = socket.create_connection((HOST, PORT), timeout=SOCKET_TIMEOUT)
            handshake = {"type": "hello", "role": "ui", "script": "restarter"}
            sock.sendall((json.dumps(handshake) + "\n").encode('utf-8'))
            sock.sendall((json.dumps({"type": "shutdown"}) + "\n").encode('utf-8'))
            sock.close()
            print("Develop server stop signal sent (for restart). Waiting for shutdown...")
            time.sleep(SHUTDOWN_WAIT)
        except Exception:
            print("No running server found. Proceeding to start.")
        # Start the server
        subprocess.Popen([sys.executable, __file__, "--serve"],
                        close_fds=True, start_new_session=True)
        print("Develop server restarted.")
        
    elif args.command == '--serve':
        # Internal: run the server loop (not meant to be called by users directly)
        server = DevelopServer()
        server.run_server()

if __name__ == "__main__":
    # Support internal "--serve" invocation to actually run the server loop
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        server = DevelopServer()
        server.run_server()
    else:
        print(f"[develop_server] Starting server on {HOST}:{PORT}, PID={os.getpid()}")
        main()
