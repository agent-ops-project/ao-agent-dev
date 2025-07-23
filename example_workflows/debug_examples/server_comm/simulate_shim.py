import socket
import json
import time
import os
import signal

HOST = '127.0.0.1'
PORT = 5959

process_id = os.getpid()
exiting = False

def cleanup():
    global exiting
    if not exiting:
        exiting = True
        try:
            msg = {"type": "deregister", "process_id": process_id}
            s.sendall((json.dumps(msg) + "\n").encode("utf-8"))
            print(f"[shim {process_id}] Sent deregister message.")
        except Exception as e:
            print(f"[shim {process_id}] Error sending deregister: {e}")
        try:
            s.close()
        except Exception:
            pass

def handle_exit(signum, frame):
    cleanup()
    exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# Connect and send handshake
s = socket.create_connection((HOST, PORT))
handshake = {"type": "hello", "role": "shim-runner", "script": "test_script.py", "process_id": process_id}
s.sendall((json.dumps(handshake) + "\n").encode("utf-8"))

# Print server's response (session_id)
print(s.recv(1024).decode())

# Send a test message
msg = {"type": "llm_log", "content": "Hello from shim!"}
s.sendall((json.dumps(msg) + "\n").encode("utf-8"))

try:
    while True:
        msg = s.recv(1024).decode()
        if msg:
            print(f"[shim {process_id}] Received: {msg}")
        time.sleep(1)
except Exception as e:
    print(f"[shim {process_id}] Exception: {e}")
finally:
    cleanup()