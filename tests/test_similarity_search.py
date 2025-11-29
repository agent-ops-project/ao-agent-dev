# tests/test_similarity_search.py

import json

import pytest

from aco.optimizations.optimization_server import OptimizationClient


class DummyDB:
    """
    Minimal fake DB that mimics exactly the methods the optimization server uses:
      - get_lesson_embedding_query
      - get_all_lesson_embeddings_except_query
    """

    def __init__(self):
        # embeddings are stored as JSON strings, just like the real DB
        self._store = {
            ("s1", "n1"): json.dumps([1.0, 0.0, 0.0]),
            ("fake_session", "fake_node"): json.dumps([1.0, 0.0, 0.0]),  # identical to target
            ("test_session", "node1"): json.dumps([0.5, 0.0, 0.0]),
            ("s3", "n3"): json.dumps([-0.2, 0.0, 0.0]),
        }

    def get_lesson_embedding_query(self, session_id, node_id):
        key = (session_id, node_id)
        if key not in self._store:
            return None
        return {
            "session_id": session_id,
            "node_id": node_id,
            "embedding": self._store[key],
        }

    def get_all_lesson_embeddings_except_query(self, session_id, node_id):
        rows = []
        for (sid, nid), emb in self._store.items():
            if (sid, nid) == (session_id, node_id):
                continue
            rows.append(
                {
                    "session_id": sid,
                    "node_id": nid,
                    "embedding": emb,
                }
            )
        return rows


def test_similarity_search_happy_path(monkeypatch):
    """
    End-to-end-ish unit test for OptimizationClient.handle_similarity_search:
    - Uses a fake DB with three other embeddings.
    - Verifies that we get a similarity_search_result with top-k sorted by score.
    """

    from aco import optimizations as opt_mod

    captured = {}

    def fake_send_json(conn, msg):
        # capture the response the optimization server would send back to the develop server
        captured["msg"] = msg

    # Patch the module-level DB and send_json used inside OptimizationClient
    monkeypatch.setattr("aco.optimizations.optimization_server.DB", DummyDB())
    monkeypatch.setattr("aco.optimizations.optimization_server.send_json", fake_send_json)

    client = OptimizationClient()
    client.conn = object()  # just a dummy, not actually used by fake_send_json

    client.handle_similarity_search(
        {"type": "similarity_search", "session_id": "s1", "node_id": "n1", "k": 3}
    )

    msg = captured["msg"]

    assert msg["type"] == "similarity_search_result"
    assert msg["session_id"] == "s1"
    assert msg["node_id"] == "n1"
    assert msg["k"] == 3

    results = msg["results"]
    # We should get exactly 3 neighbors back
    assert len(results) == 3

    # Scores should be sorted in descending order
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

    # The most similar one should be the identical embedding (fake_session, fake_node)
    top = results[0]
    assert top["session_id"] == "fake_session"
    assert top["node_id"] == "fake_node"


def test_similarity_search_no_target_embedding(monkeypatch):
    """
    If there is no embedding for (session_id, node_id), we should get an empty result list.
    """

    class EmptyDB(DummyDB):
        def get_lesson_embedding_query(self, session_id, node_id):
            return None

    captured = {}

    def fake_send_json(conn, msg):
        captured["msg"] = msg

    monkeypatch.setattr("aco.optimizations.optimization_server.DB", EmptyDB())
    monkeypatch.setattr("aco.optimizations.optimization_server.send_json", fake_send_json)

    client = OptimizationClient()
    client.conn = object()

    client.handle_similarity_search(
        {"type": "similarity_search", "session_id": "s1", "node_id": "n1", "k": 5}
    )

    msg = captured["msg"]
    assert msg["type"] == "similarity_search_result"
    assert msg["session_id"] == "s1"
    assert msg["node_id"] == "n1"
    assert msg["results"] == []
