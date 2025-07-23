import time
import os
import signal
import sys

def signal_handler(signum, frame):
    print("Received signal, shutting down gracefully...")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print("Long-running test script started!")
print(f"PID: {os.getpid()}")
print(f"Working directory: {os.getcwd()}")
print("This script will run for 60 seconds or until interrupted...")

# Simulate some work
for i in range(60):
    print(f"Working... {i+1}/60")
    time.sleep(1)

print("Script finished!") 