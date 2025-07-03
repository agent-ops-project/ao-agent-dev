import socket
import json
import time
import threading

HOST = '127.0.0.1'
PORT = 5959

# Use the same session_id as the shim, or let the server assign one
s = socket.create_connection((HOST, PORT))
handshake = {"type": "hello", "role": "ui", "script": "test_script.py"}
s.sendall((json.dumps(handshake) + "\n").encode("utf-8"))

# Print server's response (session_id)
try:
    session_info = json.loads(s.recv(1024).decode())
    print("Session info:", session_info)
except Exception as e:
    # This happens sometimes, just ignore it.
    print(f"[UI] Error receiving session info: {e}")
    # s.close()
    # exit(1)

shim_pids = []
shim_pids_lock = threading.Lock()

def listen():
    while True:
        msg = s.recv(1024).decode()
        if msg:
            print(f"[UI] Received: {msg}")
            try:
                data = json.loads(msg)
                if data.get("type") == "shim_list":
                    with shim_pids_lock:
                        shim_pids.clear()
                        shim_pids.extend(data.get("pids", []))
                elif data.get("type") == "deregister" and "process_id" in data:
                    with shim_pids_lock:
                        pid = data["process_id"]
                        if pid in shim_pids:
                            shim_pids.remove(pid)
                            print(f"[UI] Removed deregistered shim PID {pid}")
            except Exception:
                pass
        time.sleep(1)

threading.Thread(target=listen, daemon=True).start()

def periodic_restart():
    while True:
        with shim_pids_lock:
            if shim_pids:
                pid = shim_pids[0]
                msg = {"type": "restart", "process_id": pid, "content": "UI requests restart"}
                s.sendall((json.dumps(msg) + "\n").encode("utf-8"))
                print(f"[UI] Sent restart for PID {pid}")
            else:
                print("[UI] No shim registered, skipping restart.")
        time.sleep(8)

threading.Thread(target=periodic_restart, daemon=True).start()

# Keep the main thread alive
while True:
    time.sleep(10)