import sqlite3
import os
import threading
import hashlib
import json
from openai.types.responses.response import Response

DB_PATH = os.path.expanduser("~/.agent_copilot_workflow.sqlite")

# Thread-safe singleton connection
def get_conn():
    if not hasattr(get_conn, "_conn"):
        get_conn._lock = threading.Lock()
        with get_conn._lock:
            if not hasattr(get_conn, "_conn"):
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                _init_db(conn)
                get_conn._conn = conn
    return get_conn._conn

def _init_db(conn):
    c = conn.cursor()
    # Create graph_topology table
    c.execute('''
        CREATE TABLE IF NOT EXISTS graph_topology (
            session_id TEXT PRIMARY KEY,
            graph_topology TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    ''')
    # Create nodes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            session_id TEXT,
            node_id TEXT,
            model TEXT,
            input TEXT,
            input_hash TEXT,
            input_overwrite TEXT,
            output TEXT,
            color TEXT,
            label TEXT,
            api_type TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (session_id, node_id)
        )
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_nodes_lookup ON nodes(session_id, model, input_hash)
    ''')
    conn.commit()

def query_one(sql, params=()):
    conn = get_conn()
    c = conn.cursor()
    c.execute(sql, params)
    return c.fetchone()

def query_all(sql, params=()):
    conn = get_conn()
    c = conn.cursor()
    c.execute(sql, params)
    return c.fetchall()

def execute(sql, params=()):
    conn = get_conn()
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    return c.lastrowid

def hash_input(input_str):
    return hashlib.sha256(input_str.encode('utf-8')).hexdigest()

# === OpenAI v2 Response helpers ===
def v2_response_to_json(response: Response) -> str:
    """Serialize an OpenAI v2 Response object to a JSON string for storage."""
    return json.dumps(response.model_dump())

def v2_json_to_response(json_str: str) -> Response:
    """Deserialize a JSON string from the DB to an OpenAI v2 Response object."""
    data = json.loads(json_str)
    return Response(**data)

def extract_output_text(response):
    """Extract the output string from a Response object or dict."""
    if hasattr(response, 'get_raw'):
        response = response.get_raw()
    try:
        # v2 OpenAI Response object or dict
        return response.output[0].content[0].text
    except Exception:
        try:
            # If dict
            return response['output'][0]['content'][0]['text']
        except Exception:
            return str(response) 