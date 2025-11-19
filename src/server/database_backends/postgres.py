"""
PostgreSQL database backend for workflow experiments.
"""
import json
import dill
import psycopg2
import psycopg2.extras
import psycopg2.pool
import threading
import inspect
from urllib.parse import urlparse

from aco.common.logger import logger
from aco.common.constants import REMOTE_DATABASE_URL
from aco.common.utils import hash_input

# Global shared connection
_shared_conn = None
_connection_params = None
_connection_lock = threading.Lock()


def _init_connection():
    """Initialize the shared connection if not already created"""
    global _shared_conn, _connection_params
    
    if _shared_conn is None:
        database_url = REMOTE_DATABASE_URL
        if not database_url:
            raise ValueError(
                "REMOTE_DATABASE_URL is required for Postgres connection (check config.yaml)"
            )
        
        # Parse the connection string
        result = urlparse(database_url)
        
        # Store connection parameters for reconnection
        _connection_params = {
            'host': result.hostname,
            'port': result.port or 5432,
            'user': result.username,
            'password': result.password,
            'database': result.path[1:],  # Remove leading '/'
            'connect_timeout': 30,
        }
        
        # Create the shared connection
        _shared_conn = psycopg2.connect(**_connection_params)
        _shared_conn.autocommit = False  # Explicit transaction control
        
        # Initialize database schema
        _init_db(_shared_conn)
        logger.info(f"Initialized PostgreSQL shared connection to {result.hostname}")


def _ensure_connection():
    """Ensure we have a working connection, reconnecting if necessary"""
    global _shared_conn
    
    with _connection_lock:
        # First check if we need to initialize
        if _shared_conn is None:
            _init_connection()
            return _shared_conn
        
        # Check if existing connection is still alive
        try:
            with _shared_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            # Connection is good
            return _shared_conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            logger.warning(f"PostgreSQL connection lost: {e}, reconnecting...")
            try:
                _shared_conn.close()
            except:
                pass  # Ignore errors when closing broken connection
            
            # Reconnect
            _shared_conn = psycopg2.connect(**_connection_params)
            _shared_conn.autocommit = False
            logger.info("PostgreSQL connection restored")
            return _shared_conn


def get_conn():
    """Get the shared connection (for compatibility with DatabaseManager)"""
    return _ensure_connection()


def return_conn(conn):
    """Return connection (no-op for shared connection)"""
    pass  # No-op since we're using a shared connection


def close_all_connections():
    """Close the shared connection"""
    global _shared_conn
    with _connection_lock:
        if _shared_conn:
            try:
                _shared_conn.close()
            except:
                pass
            _shared_conn = None
            logger.debug("Closed PostgreSQL shared connection")


def _init_db(conn):
    """Initialize database schema (create tables if not exist)"""
    c = conn.cursor()
    
    # Create experiments table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS experiments (
            session_id TEXT PRIMARY KEY,
            parent_session_id TEXT,
            graph_topology TEXT,
            color_preview TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cwd TEXT,
            command TEXT,
            environment TEXT,
            code_hash TEXT,
            name TEXT,
            success TEXT CHECK (success IN ('', 'Satisfactory', 'Failed')),
            notes TEXT,
            log TEXT,
            FOREIGN KEY (parent_session_id) REFERENCES experiments (session_id),
            UNIQUE (parent_session_id, name)
        )
    """
    )
    
    # Create llm_calls table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_calls (
            session_id TEXT,
            node_id TEXT,
            input BYTEA,
            input_hash TEXT,
            input_overwrite BYTEA,
            output TEXT,
            color TEXT,
            label TEXT,
            api_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (session_id, node_id),
            FOREIGN KEY (session_id) REFERENCES experiments (session_id)
        )
    """
    )
    
    # Create attachments table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS attachments (
            file_id TEXT PRIMARY KEY,
            session_id TEXT,
            line_no INTEGER,
            content_hash TEXT,
            file_path TEXT,
            taint TEXT,
            FOREIGN KEY (session_id) REFERENCES experiments (session_id)
        )
    """
    )
    
    # Create indexes
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS attachments_content_hash_idx ON attachments(content_hash)
    """
    )
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS original_input_lookup ON llm_calls(session_id, input_hash)
    """
    )
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS experiments_timestamp_idx ON experiments(timestamp DESC)
    """
    )
    
    conn.commit()
    logger.debug("Database schema initialized")


def query_one(sql, params=()):
    """Execute a query and return one result"""
    # Convert SQLite placeholders (?) to PostgreSQL placeholders (%s)
    sql = sql.replace("?", "%s")
    
    thread_id = threading.get_ident()
    logger.info(f"[QUERY_ONE] START thread={thread_id} sql={sql[:100]}...")
    
    try:
        conn = _ensure_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone()
        conn.commit()
        logger.info(f"[QUERY_ONE] SUCCESS thread={thread_id} conn={id(conn)} result={'Found' if result else 'None'}")
        return result
    except Exception as e:
        logger.error(f"[QUERY_ONE] ERROR thread={thread_id} error={e}")
        try:
            conn = _ensure_connection()
            conn.rollback()
        except:
            pass
        raise


def query_all(sql, params=()):
    """Execute a query and return all results"""
    # Convert SQLite placeholders (?) to PostgreSQL placeholders (%s)
    sql = sql.replace("?", "%s")
    
    thread_id = threading.get_ident()
    logger.info(f"[QUERY_ALL] START thread={thread_id} sql={sql[:100]}...")
    
    try:
        conn = _ensure_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchall()
        conn.commit()
        logger.info(f"[QUERY_ALL] SUCCESS thread={thread_id} conn={id(conn)} rows={len(result)}")
        return result
    except Exception as e:
        logger.error(f"[QUERY_ALL] ERROR thread={thread_id} error={e}")
        try:
            conn = _ensure_connection()
            conn.rollback()
        except:
            pass
        raise


def execute(sql, params=()):
    """Execute SQL statement"""
    # Convert SQLite placeholders (?) to PostgreSQL placeholders (%s)
    sql = sql.replace("?", "%s")
    
    thread_id = threading.get_ident()
    logger.info(f"[EXECUTE] START thread={thread_id} sql={sql[:100]}...")
    
    try:
        conn = _ensure_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            lastrowid = cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
        conn.commit()
        logger.info(f"[EXECUTE] SUCCESS thread={thread_id} conn={id(conn)}")
        return lastrowid
    except Exception as e:
        logger.error(f"[EXECUTE] ERROR thread={thread_id} error={e}")
        try:
            conn = _ensure_connection()
            conn.rollback()
        except:
            pass
        raise


def deserialize_input(input_blob, api_type=None):
    """Deserialize input blob back to original dict"""
    if input_blob is None:
        return None
    # Postgres stores as bytes directly
    return dill.loads(bytes(input_blob))


def deserialize(output_json, api_type=None):
    """Deserialize output JSON back to response object"""
    if output_json is None:
        return None
    # Handle the case where dill pickled data was stored as TEXT
    # When binary data is stored as TEXT in PostgreSQL, we need to convert it back to bytes
    if isinstance(output_json, str):
        # Convert string back to bytes for dill.loads()
        output_json = output_json.encode('latin1')
    return dill.loads(output_json)


def store_taint_info(session_id, file_path, line_no, taint_nodes):
    """Store taint information for a line in a file"""
    file_id = f"{session_id}:{file_path}:{line_no}"
    content_hash = hash_input(f"{file_path}:{line_no}")
    taint_json = json.dumps(taint_nodes) if taint_nodes else "[]"

    logger.debug(f"Storing taint info for {file_id}: {taint_json}")

    execute(
        """
        INSERT INTO attachments (file_id, session_id, line_no, content_hash, file_path, taint)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (file_id) DO UPDATE SET
            session_id = EXCLUDED.session_id,
            line_no = EXCLUDED.line_no,
            content_hash = EXCLUDED.content_hash,
            file_path = EXCLUDED.file_path,
            taint = EXCLUDED.taint
        """,
        (file_id, session_id, line_no, content_hash, file_path, taint_json),
    )


def get_taint_info(file_path, line_no):
    """Get taint information for a specific line in a file from any previous session"""
    row = query_one(
        """
        SELECT session_id, taint FROM attachments 
        WHERE file_path = %s AND line_no = %s
        ORDER BY ctid DESC
        LIMIT 1
        """,
        (file_path, line_no),
    )
    if row:
        logger.debug(f"Taint info for {file_path}:{line_no}: {row['taint']}")
        taint_nodes = json.loads(row["taint"]) if row["taint"] else []
        return row["session_id"], taint_nodes
    return None, []


def add_experiment_query(session_id, parent_session_id, name, default_graph, timestamp, cwd, command, env_json, default_success, default_note, default_log):
    """Execute PostgreSQL-specific INSERT for experiments table"""
    execute(
        """INSERT INTO experiments (session_id, parent_session_id, name, graph_topology, timestamp, cwd, command, environment, success, notes, log) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (session_id) DO UPDATE SET
               parent_session_id = EXCLUDED.parent_session_id,
               name = EXCLUDED.name,
               graph_topology = EXCLUDED.graph_topology,
               timestamp = EXCLUDED.timestamp,
               cwd = EXCLUDED.cwd,
               command = EXCLUDED.command,
               environment = EXCLUDED.environment,
               success = EXCLUDED.success,
               notes = EXCLUDED.notes,
               log = EXCLUDED.log""",
        (
            session_id,
            parent_session_id,
            name,
            default_graph,
            timestamp,
            cwd,
            command,
            env_json,
            default_success,
            default_note,
            default_log,
        ),
    )


def set_input_overwrite_query(input_overwrite, session_id, node_id):
    """Execute PostgreSQL-specific UPDATE for llm_calls input_overwrite"""
    execute(
        "UPDATE llm_calls SET input_overwrite=%s, output=NULL WHERE session_id=%s AND node_id=%s",
        (input_overwrite, session_id, node_id),
    )


def set_output_overwrite_query(output_overwrite, session_id, node_id):
    """Execute PostgreSQL-specific UPDATE for llm_calls output"""
    execute(
        "UPDATE llm_calls SET output=%s WHERE session_id=%s AND node_id=%s",
        (output_overwrite, session_id, node_id),
    )


def delete_llm_calls_query(session_id):
    """Execute PostgreSQL-specific DELETE for llm_calls"""
    execute("DELETE FROM llm_calls WHERE session_id=%s", (session_id,))


def update_experiment_graph_topology_query(graph_json, session_id):
    """Execute PostgreSQL-specific UPDATE for experiments graph_topology"""
    execute(
        "UPDATE experiments SET graph_topology=%s WHERE session_id=%s", (graph_json, session_id)
    )


def update_experiment_timestamp_query(timestamp, session_id):
    """Execute PostgreSQL-specific UPDATE for experiments timestamp"""
    execute("UPDATE experiments SET timestamp=%s WHERE session_id=%s", (timestamp, session_id))


def update_experiment_name_query(run_name, session_id):
    """Execute PostgreSQL-specific UPDATE for experiments name"""
    execute(
        "UPDATE experiments SET name=%s WHERE session_id=%s",
        (run_name, session_id),
    )


def update_experiment_result_query(result, session_id):
    """Execute PostgreSQL-specific UPDATE for experiments success"""
    execute(
        "UPDATE experiments SET success=%s WHERE session_id=%s",
        (result, session_id),
    )


def update_experiment_notes_query(notes, session_id):
    """Execute PostgreSQL-specific UPDATE for experiments notes"""
    execute(
        "UPDATE experiments SET notes=%s WHERE session_id=%s",
        (notes, session_id),
    )


def update_experiment_log_query(updated_log, updated_success, color_preview_json, graph_json, session_id):
    """Execute PostgreSQL-specific UPDATE for experiments log, success, color_preview, and graph_topology"""
    execute(
        "UPDATE experiments SET log=%s, success=%s, color_preview=%s, graph_topology=%s WHERE session_id=%s",
        (updated_log, updated_success, color_preview_json, graph_json, session_id),
    )