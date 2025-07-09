import socket
import json
import time
import threading

HOST = '127.0.0.1'
PORT = 5959

def test_process_list():
    """Test the process list functionality by connecting as a UI client."""
    print("Connecting to develop server as UI client...")
    
    # Connect as UI client
    ui_socket = socket.create_connection((HOST, PORT))
    handshake = {"type": "hello", "role": "ui", "script": "test_ui"}
    ui_socket.sendall((json.dumps(handshake) + "\n").encode("utf-8"))
    
    # Read session info
    try:
        file_obj = ui_socket.makefile(mode='r')
        session_line = file_obj.readline()
        if session_line:
            session_info = json.loads(session_line.strip())
            print("Session info:", session_info)
    except Exception as e:
        print(f"Error receiving session info: {e}")
    
    # Listen for messages
    def listen_for_messages():
        try:
            for line in file_obj:
                try:
                    msg = json.loads(line.strip())
                    print(f"[UI] Received message: {msg}")
                    if msg.get("type") == "experiment_list":
                        processes = msg.get("processes", [])
                        print(f"[UI] Process list received: {len(processes)} processes")
                        for proc in processes:
                            print(f"  - PID {proc['pid']}: {proc['script_name']} ({proc['status']})")
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"[UI] Error receiving data: {e}")
    
    # Start listening thread
    listen_thread = threading.Thread(target=listen_for_messages, daemon=True)
    listen_thread.start()
    
    # Keep the connection alive for a while
    print("Listening for process list updates...")
    time.sleep(10)
    
    ui_socket.close()
    print("Test completed.")

if __name__ == "__main__":
    test_process_list() 