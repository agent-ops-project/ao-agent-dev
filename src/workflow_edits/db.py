import os
import sqlite3
import threading
import hashlib
from common.logger import logger
from common.constants import ACO_DB_PATH


# Thread-safe singleton connection
def get_conn():
    db_path = os.path.join(ACO_DB_PATH, "experiments.sqlite")
    if not hasattr(get_conn, "_conn"):
        get_conn._lock = threading.Lock()
        with get_conn._lock:
            if not hasattr(get_conn, "_conn"):
                conn = sqlite3.connect(db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                _init_db(conn)
                logger.debug(f"Initialized DB at {db_path}")
                get_conn._conn = conn
    return get_conn._conn


def _init_db(conn):
    c = conn.cursor()
    # Create experiments table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS experiments (
            session_id TEXT PRIMARY KEY,
            graph_topology TEXT,
            color_preview TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            cwd TEXT,
            command TEXT,
            environment TEXT,
            code_hash TEXT,
            title TEXT,
            success TEXT CHECK (success IN ('', 'Satisfatory', 'Failed')),
            notes TEXT,
            log TEXT
        )
    """
    )
    # Create llm_calls table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_calls (
            session_id TEXT,
            node_id TEXT,
            model TEXT,
            input TEXT,
            input_hash TEXT,
            input_overwrite TEXT,
            input_overwrite_hash TEXT,
            output TEXT,
            color TEXT,
            label TEXT,
            api_type TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (session_id, node_id)
        )
    """
    )
    # Create attachments table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS attachments (
            file_id TEXT PRIMARY KEY,
            content_hash TEXT,
            file_path TEXT
        )
    """
    )
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS attachments_content_hash_idx ON attachments(content_hash)
    """
    )
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS original_input_lookup ON llm_calls(session_id, model, input_hash)
    """
    )
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS overwrite_input_lookup ON llm_calls(session_id, model, input_overwrite_hash)
    """
    )
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS experiments_timestamp_idx ON experiments(timestamp DESC)
    """
    )
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
    return hashlib.sha256(input_str.encode("utf-8")).hexdigest()
