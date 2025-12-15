"""Unit tests for TaintWrapper (dict) functionality."""

import pytest

from aco.runner.taint_wrappers import taint_wrap, TaintWrapper, get_taint_origins


class TestTaintDict:
    """Test suite for TaintWrapper (dict) functionality."""

    def test_creation(self):
        """Test TaintWrapper creation with various taint origins."""
        # Test with no taint
        d1 = {"a": 1, "b": 2}  # No wrapping for no taint
        assert dict(d1) == {"a": 1, "b": 2}
        assert get_taint_origins(d1) == []

        # Test with single string taint
        d2 = taint_wrap({"x": 10}, taint_origin="source1")
        assert isinstance(d2, TaintWrapper)
        assert dict(d2) == {"x": 10}
        assert d2._taint_origin == ["source1"]

        # Test with single int taint
        d3 = taint_wrap({"key": "value"}, taint_origin=999)
        assert dict(d3) == {"key": "value"}
        assert d3._taint_origin == [999]

        # Test with list taint
        d4 = taint_wrap({}, taint_origin=["source1", "source2"])
        assert dict(d4) == {}
        assert d4._taint_origin == ["source1", "source2"]

        # Test with tainted values
        tainted_str = taint_wrap("tainted", taint_origin="value_source")
        d5 = {"key": tainted_str, "normal": "value"}  # Simple dict for this test
        # Check that taint origins can be extracted from values
        expected_taint = ["value_source"]
        assert get_taint_origins(d5) == expected_taint

        # Test invalid taint origin type
        with pytest.raises(TypeError):
            taint_wrap({"a": 1}, taint_origin={})

    def test_setitem_getitem(self):
        """Test __setitem__ and __getitem__ methods."""
        d = taint_wrap({"a": 1}, taint_origin="original")

        # Set normal value
        d["b"] = 2
        assert d["b"] == 2
        assert dict(d) == {"a": 1, "b": 2}
        assert get_taint_origins(d) == ["original"]

        # Set tainted value
        tainted = taint_wrap("tainted", taint_origin="new_value")
        d["c"] = tainted
        assert d["c"] == tainted
        assert dict(d) == {"a": 1, "b": 2, "c": tainted}
        expected_taint = set(["original", "new_value"])
        assert set(get_taint_origins(d)) == expected_taint

        # Override existing key
        d["a"] = tainted
        assert d["a"] == tainted
        # Should still have both taints
        assert set(get_taint_origins(d)) == expected_taint

    def test_delitem(self):
        """Test __delitem__ method."""
        tainted1 = taint_wrap("t1", taint_origin="value1")
        tainted2 = taint_wrap("t2", taint_origin="value2")
        d = taint_wrap({"a": tainted1, "b": "normal", "c": tainted2}, taint_origin="original")

        # Delete key with normal value
        del d["b"]
        assert dict(d) == {"a": tainted1, "c": tainted2}
        # Should recompute taint from remaining values
        expected_taint = set(["original", "value1", "value2"])
        assert set(get_taint_origins(d)) == expected_taint

        # Delete key with tainted value
        del d["a"]
        assert dict(d) == {"c": tainted2}
        # Should only have taint from remaining values
        assert set(get_taint_origins(d)) == {"original", "value2"}

    def test_update(self):
        """Test update method."""
        d = taint_wrap({"a": 1}, taint_origin="original")

        # Update with normal dict
        d.update({"b": 2, "c": 3})
        assert dict(d) == {"a": 1, "b": 2, "c": 3}
        assert get_taint_origins(d) == ["original"]

        # Update with tainted values
        tainted1 = taint_wrap("t1", taint_origin="update1")
        tainted2 = taint_wrap("t2", taint_origin="update2")
        d.update({"d": tainted1, "e": tainted2})
        assert dict(d) == {"a": 1, "b": 2, "c": 3, "d": tainted1, "e": tainted2}
        expected_taint = set(["original", "update1", "update2"])
        assert set(get_taint_origins(d)) == expected_taint

        # Update with keyword arguments
        tainted3 = taint_wrap("t3", taint_origin="kwarg")
        d.update(f=tainted3, g="normal")
        assert d["f"] == tainted3
        assert d["g"] == "normal"
        expected_taint.add("kwarg")
        assert set(get_taint_origins(d)) == expected_taint

        # Update with list of tuples
        tainted4 = taint_wrap("t4", taint_origin="tuple")
        d.update([("h", tainted4), ("i", "normal")])
        assert d["h"] == tainted4
        assert d["i"] == "normal"
        expected_taint.add("tuple")
        assert set(get_taint_origins(d)) == expected_taint

    def test_setdefault(self):
        """Test setdefault method."""
        d = taint_wrap({"a": 1}, taint_origin="original")

        # setdefault with existing key
        result = d.setdefault("a", 999)
        assert result == 1
        assert dict(d) == {"a": 1}
        assert get_taint_origins(d) == ["original"]

        # setdefault with new key (normal default)
        result = d.setdefault("b", 2)
        assert result == 2
        assert dict(d) == {"a": 1, "b": 2}
        assert get_taint_origins(d) == ["original"]

        # setdefault with new key (tainted default)
        tainted = taint_wrap("default", taint_origin="default_value")
        result = d.setdefault("c", tainted)
        assert result == tainted
        assert dict(d) == {"a": 1, "b": 2, "c": tainted}
        expected_taint = set(["original", "default_value"])
        assert set(get_taint_origins(d)) == expected_taint

        # setdefault with no default (None)
        result = d.setdefault("d")
        assert result is None
        assert d["d"] is None

    def test_pop(self):
        """Test pop method."""
        tainted1 = taint_wrap("t1", taint_origin="value1")
        tainted2 = taint_wrap("t2", taint_origin="value2")
        d = taint_wrap({"a": tainted1, "b": "normal", "c": tainted2}, taint_origin="original")

        # Pop existing key
        popped = d.pop("b")
        assert popped == "normal"
        assert dict(d) == {"a": tainted1, "c": tainted2}
        # Should recompute taint
        expected_taint = set(["original", "value1", "value2"])
        assert set(get_taint_origins(d)) == expected_taint

        # Pop with default
        result = d.pop("missing", "default")
        assert result == "default"
        # Dict should be unchanged
        assert dict(d) == {"a": tainted1, "c": tainted2}

        # Pop missing key without default (should raise KeyError)
        with pytest.raises(KeyError):
            d.pop("missing")

    def test_popitem(self):
        """Test popitem method."""
        tainted1 = taint_wrap("t1", taint_origin="value1")
        tainted2 = taint_wrap("t2", taint_origin="value2")
        d = taint_wrap({"a": tainted1, "b": tainted2}, taint_origin="original")

        # Pop an item
        key, value = d.popitem()
        assert key in ["a", "b"]
        assert value in [tainted1, tainted2]
        assert len(d) == 1

        # Should recompute taint from remaining values
        remaining_taint = set(get_taint_origins(d))
        if key == "a":
            assert remaining_taint == {"original", "value2"}
        else:
            assert remaining_taint == {"original", "value1"}

        # Pop last item
        d.popitem()
        assert len(d) == 0
        assert get_taint_origins(d) == ["original"]  # Still has dict taint

        # Pop from empty dict (should raise KeyError)
        with pytest.raises(KeyError):
            d.popitem()

    def test_clear(self):
        """Test clear method."""
        tainted = taint_wrap("tainted", taint_origin="value")
        d = taint_wrap({"a": 1, "b": tainted}, taint_origin="original")

        d.clear()
        assert dict(d) == {}
        # Still retains the original dict taint
        assert d._taint_origin == ["original"]

    def test_get_raw(self):
        """Test getting raw object."""
        tainted = taint_wrap("tainted", taint_origin="value")
        d = taint_wrap({"a": 1, "b": tainted, "c": "normal"}, taint_origin="original")

        raw = d.obj
        expected = {"a": 1, "b": tainted, "c": "normal"}
        assert raw == expected
        assert isinstance(raw, dict)
        assert not isinstance(raw, TaintWrapper)
        assert isinstance(raw["b"], TaintWrapper)  # Items still wrapped

    def test_dict_methods(self):
        """Test standard dict methods work correctly."""
        tainted = taint_wrap("tainted", taint_origin="value")
        d = taint_wrap({"a": 1, "b": tainted, "c": 3}, taint_origin="original")

        # keys()
        keys = list(d.keys())
        assert set(keys) == {"a", "b", "c"}

        # values()
        values = list(d.values())
        assert set(values) == {1, tainted, 3}

        # items()
        items = list(d.items())
        expected_items = {("a", 1), ("b", tainted), ("c", 3)}
        assert set(items) == expected_items

        # get()
        assert d.get("a") == 1
        assert d.get("b") == tainted
        assert d.get("missing") is None
        assert d.get("missing", "default") == "default"

    def test_dict_operations(self):
        """Test dict-like operations."""
        tainted = taint_wrap("tainted", taint_origin="value")
        d = taint_wrap({"a": 1, "b": tainted}, taint_origin="original")

        # len
        assert len(d) == 2

        # in operator
        assert "a" in d
        assert "b" in d
        assert "missing" not in d

        # iter (iterates over keys)
        keys = []
        for key in d:
            keys.append(key)
        assert set(keys) == {"a", "b"}

        # bool
        assert bool(d) is True
        empty = taint_wrap({}, taint_origin="empty")
        assert bool(empty) is False

    def test_nested_taint_propagation(self):
        """Test taint propagation with nested structures."""
        # Create nested tainted items
        inner_dict = taint_wrap({"x": 1}, taint_origin="inner")
        tainted_str = taint_wrap("nested", taint_origin="string")

        outer = taint_wrap({"inner": inner_dict, "str": tainted_str}, taint_origin="outer")

        # Should have taint from all sources
        expected_taint = set(["outer", "inner", "string"])
        assert set(get_taint_origins(outer)) == expected_taint

        # Modify inner dict
        inner_dict["y"] = taint_wrap("new", taint_origin="added")

        # Outer dict should still have its original taint
        # (it doesn't automatically update from changes to contained objects)
        assert set(get_taint_origins(outer)) == expected_taint

    def test_comparison_with_regular_dicts(self):
        """Test that TaintWrapper behaves like regular dict in comparisons."""
        d1 = taint_wrap({"a": 1, "b": 2}, taint_origin="source1")
        d2 = {"a": 1, "b": 2}
        d3 = taint_wrap({"a": 1, "b": 2}, taint_origin="source2")

        # Should be equal regardless of taint
        assert d1 == d2
        assert d1 == d3
        assert d2 == d3

        # Different contents should not be equal
        d4 = taint_wrap({"a": 1, "b": 3}, taint_origin="source1")
        assert d1 != d4

    def test_copy_operations(self):
        """Test copy and deepcopy operations."""
        import copy

        tainted = taint_wrap("tainted", taint_origin="value")
        d = taint_wrap({"a": 1, "b": tainted}, taint_origin="original")

        # Shallow copy using dict.copy()
        d_copy = d.copy()
        assert dict(d_copy) == dict(d)
        assert isinstance(d_copy, dict)  # Standard copy returns regular dict

        # The original taint information is not preserved in standard copy
        # This is expected behavior since copy() returns a regular dict

        # Deep copy
        d_deep = copy.deepcopy(d)
        assert dict(d_deep) == {"a": 1, "b": tainted}  # Items maintain their wrapping
        assert not isinstance(d_deep, TaintWrapper)  # Copy returns raw object

    def test_fromkeys_classmethod(self):
        """Test dict.fromkeys() if available."""
        # Note: TaintWrapper doesn't explicitly implement fromkeys,
        # so it would use the default dict.fromkeys which returns a regular dict
        keys = ["a", "b", "c"]
        tainted_value = taint_wrap("default", taint_origin="default")

        # This creates a regular dict, not a TaintWrapper
        result = dict.fromkeys(keys, tainted_value)
        assert isinstance(result, dict)
        assert not isinstance(result, TaintWrapper)
        assert dict(result) == {"a": tainted_value, "b": tainted_value, "c": tainted_value}
