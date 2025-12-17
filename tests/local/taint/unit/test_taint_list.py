"""Unit tests for TaintWrapper (list) functionality."""

import pytest

from aco.runner.taint_wrappers import taint_wrap, get_taint_origins
from ....utils import with_ast_rewriting_class


@with_ast_rewriting_class
class TestTaintList:
    """Test suite for TaintWrapper (list) functionality."""

    def test_creation(self):
        """Test TaintWrapper creation with various taint origins."""
        # Test with no taint
        l1 = [1, 2, 3]  # No wrapping for no taint
        assert list(l1) == [1, 2, 3]
        assert get_taint_origins(l1) == []

        # Test with single string taint
        l2 = taint_wrap(["a", "b"], taint_origin="source1")
        assert list(l2) == ["a", "b"]
        assert l2._taint_origin == ["source1"]

        # Test with single int taint
        l3 = taint_wrap([10], taint_origin=999)
        assert list(l3) == [10]
        assert l3._taint_origin == [999]

        # Test with list taint
        l4 = taint_wrap([], taint_origin=["source1", "source2"])
        assert list(l4) == []
        assert l4._taint_origin == ["source1", "source2"]

        # Test with tainted items
        tainted_str = taint_wrap("tainted", taint_origin="item_source")
        l5 = [tainted_str, "normal"]  # Let's create a simple list for this test
        # Check that taint origins can be extracted from items
        expected_taint = ["item_source"]
        assert get_taint_origins(l5) == expected_taint

        # Test invalid taint origin type
        with pytest.raises(TypeError):
            taint_wrap([1, 2], taint_origin={})

    def test_append(self):
        """Test append method."""
        l = taint_wrap([1, 2], taint_origin="original")

        # Append normal item
        l.append(3)
        assert list(l) == [1, 2, 3]
        assert get_taint_origins(l) == ["original"]

        # Append tainted item
        tainted = taint_wrap("tainted", taint_origin="new_item")
        l.append(tainted)
        assert list(l) == [1, 2, 3, tainted]
        expected_taint = set(["original", "new_item"])
        assert set(get_taint_origins(l)) == expected_taint, f"{set(get_taint_origins(l))}"

    def test_obj(self):
        class SomeObj:
            def __init__(self, x, y):
                self.list = [x, y]

            def add_to_list(self, z):
                self.list.append(z)

        tainted = taint_wrap(3, taint_origin="new_item")
        o = taint_wrap(SomeObj(1, 2))
        o.add_to_list(tainted)
        assert get_taint_origins(o.list[-1]) == ["new_item"], f"{get_taint_origins(o.list[-1])}"

    def test_extend(self):
        """Test extend method."""
        l = taint_wrap([1, 2], taint_origin="original")

        # Extend with normal items
        l.extend([3, 4])
        assert list(l) == [1, 2, 3, 4]
        assert get_taint_origins(l) == ["original"]

        # Extend with tainted items
        tainted1 = taint_wrap("t1", taint_origin="ext1")
        tainted2 = taint_wrap("t2", taint_origin="ext2")
        l.extend([tainted1, tainted2])
        assert list(l) == [1, 2, 3, 4, tainted1, tainted2]
        expected_taint = set(["original", "ext1", "ext2"])
        assert set(get_taint_origins(l)) == expected_taint

    def test_setitem(self):
        """Test __setitem__ method."""
        l = taint_wrap([1, 2, 3, 4], taint_origin="original")

        # Set single item (normal)
        l[0] = 10
        assert list(l) == [10, 2, 3, 4]
        assert get_taint_origins(l) == ["original"]

        # Set single item (tainted)
        tainted = taint_wrap("tainted", taint_origin="new_item")
        l[1] = tainted
        assert list(l) == [10, tainted, 3, 4]
        expected_taint = set(["original", "new_item"])
        assert set(get_taint_origins(l)) == expected_taint

        # Set slice
        l[2:4] = [30, 40]
        assert list(l) == [10, tainted, 30, 40]
        # Should still have both taints
        assert set(get_taint_origins(l)) == expected_taint

        # Set slice with tainted items
        tainted_slice = [taint_wrap("s1", "slice1"), taint_wrap("s2", "slice2")]
        l[0:2] = tainted_slice
        assert list(l) == [tainted_slice[0], tainted_slice[1], 30, 40]
        expected_taint = set(["original", "new_item", "slice1", "slice2"])
        assert set(get_taint_origins(l)) == expected_taint

    def test_delitem(self):
        """Test __delitem__ method."""
        tainted1 = taint_wrap("t1", taint_origin="item1")
        tainted2 = taint_wrap("t2", taint_origin="item2")
        l = taint_wrap([tainted1, "normal", tainted2], taint_origin="original")

        # Delete single item
        del l[1]  # Remove "normal"
        assert list(l) == [tainted1, tainted2]
        # Should recompute taint from remaining items
        expected_taint = set(["item1", "item2"])
        assert set(get_taint_origins(l)) == expected_taint

        # Delete slice
        l = taint_wrap([1, tainted1, 3, tainted2, 5], taint_origin="original")
        del l[1:4]  # Remove tainted1, 3, tainted2
        assert list(l) == [1, 5]
        # Should only have original taint now
        assert get_taint_origins(l) == ["original"]  # Still has list taint

    def test_insert(self):
        """Test insert method."""
        l = taint_wrap([1, 3], taint_origin="original")

        # Insert normal item
        l.insert(1, 2)
        assert list(l) == [1, 2, 3]
        assert get_taint_origins(l) == ["original"]

        # Insert tainted item
        tainted = taint_wrap("inserted", taint_origin="inserted_item")
        l.insert(0, tainted)
        assert list(l) == [tainted, 1, 2, 3]
        expected_taint = set(["original", "inserted_item"])
        assert set(get_taint_origins(l)) == expected_taint

    def test_pop(self):
        """Test pop method."""
        tainted1 = taint_wrap("t1", taint_origin="item1")
        tainted2 = taint_wrap("t2", taint_origin="item2")
        l = taint_wrap([tainted1, "normal", tainted2], taint_origin="original")

        # Pop last item
        popped = l.pop()
        assert popped == tainted2
        assert list(l) == [tainted1, "normal"]
        # Should recompute taint
        assert set(get_taint_origins(l)) == {"original", "item1"}

        # Pop specific index
        popped = l.pop(0)
        assert popped == tainted1
        assert list(l) == ["normal"]
        # Should still have original list taint
        assert get_taint_origins(l) == ["original"]

    def test_remove(self):
        """Test remove method."""
        tainted1 = taint_wrap("t1", taint_origin="item1")
        tainted2 = taint_wrap("t2", taint_origin="item2")
        l = taint_wrap([tainted1, "normal", tainted2, tainted1], taint_origin="original")

        # Remove first occurrence
        l.remove(tainted1)
        assert list(l) == ["normal", tainted2, tainted1]
        # Should still have both item taints and original
        expected_taint = set(["original", "item1", "item2"])
        assert set(get_taint_origins(l)) == expected_taint

    def test_clear(self):
        """Test clear method."""
        tainted = taint_wrap("tainted", taint_origin="item")
        l = taint_wrap([1, tainted, 3], taint_origin="original")

        l.clear()
        assert list(l) == []
        # Still retains the original list taint
        assert l._taint_origin == ["original"]

    def test_iadd(self):
        """Test += operator."""
        l = taint_wrap([1, 2], taint_origin="original")

        # += with normal list
        l += [3, 4]
        assert list(l) == [1, 2, 3, 4]
        assert get_taint_origins(l) == ["original"]

        # += with tainted items
        tainted = taint_wrap("tainted", taint_origin="added")
        l += [tainted]
        assert list(l) == [1, 2, 3, 4, tainted]
        expected_taint = set(["original", "added"])
        assert set(get_taint_origins(l)) == expected_taint

        # Verify it returns self
        result = l
        l += [5]
        assert l is result

    def test_imul(self):
        """Test *= operator."""
        tainted = taint_wrap("t", taint_origin="item")
        l = taint_wrap([1, tainted], taint_origin="original")

        l *= 3
        expected = [1, tainted, 1, tainted, 1, tainted]
        assert list(l) == expected
        # Should still have both taints
        expected_taint = set(["original", "item"])
        assert set(get_taint_origins(l)) == expected_taint

        # Verify it returns self
        result = l
        l *= 1
        assert l is result

    def test_get_raw(self):
        """Test getting raw object."""
        tainted = taint_wrap("tainted", taint_origin="item")
        l = taint_wrap([1, tainted, 3], taint_origin="original")

        raw = l.obj
        assert raw == [1, tainted, 3]  # Returns list with wrapped items
        assert isinstance(raw, list)

    def test_list_methods(self):
        """Test standard list methods work correctly."""
        tainted = taint_wrap("tainted", taint_origin="item")
        l = taint_wrap([1, tainted, 3, tainted], taint_origin="original")

        # count
        assert l.count(tainted) == 2
        assert l.count(1) == 1
        assert l.count("missing") == 0

        # index
        assert l.index(tainted) == 1
        assert l.index(3) == 2

        # reverse
        l.reverse()
        expected = [tainted, 3, tainted, 1]
        assert list(l) == expected
        # Taint should be preserved
        expected_taint = set(["original", "item"])
        assert set(get_taint_origins(l)) == expected_taint

        # sort (if items are comparable)
        l2 = taint_wrap([3, 1, 2], taint_origin="sortable")
        l2.sort()
        assert list(l2) == [1, 2, 3]
        assert get_taint_origins(l2) == ["sortable"]

    def test_list_operations(self):
        """Test list-like operations."""
        tainted1 = taint_wrap("t1", taint_origin="item1")
        tainted2 = taint_wrap("t2", taint_origin="item2")
        l = taint_wrap([1, tainted1, 3], taint_origin="original")

        # len
        assert len(l) == 3

        # in operator
        assert 1 in l
        assert tainted1 in l
        assert "missing" not in l

        # iter
        items = []
        for item in l:
            items.append(item)
        assert items == [1, tainted1, 3]

        # bool
        assert bool(l) is True
        empty = taint_wrap([], taint_origin="empty")
        assert bool(empty) is False

    def test_nested_taint_propagation(self):
        """Test taint propagation with nested structures."""
        # Create nested tainted items
        inner_list = taint_wrap([1, 2], taint_origin="inner")
        tainted_str = taint_wrap("nested", taint_origin="string")

        outer = taint_wrap([inner_list, tainted_str], taint_origin="outer")

        # Should have taint from all sources
        expected_taint = set(["outer", "inner", "string"])
        assert set(get_taint_origins(outer)) == expected_taint

        # Modify inner list
        inner_list.append(taint_wrap("new", taint_origin="added"))

        # Outer list should still have its original taint
        # (it doesn't automatically update from changes to contained objects)
        assert set(get_taint_origins(outer)) == expected_taint

    def test_comparison_with_regular_lists(self):
        """Test that TaintWrapper behaves like regular list in comparisons."""
        l1 = taint_wrap([1, 2, 3], taint_origin="source1")
        l2 = [1, 2, 3]
        l3 = taint_wrap([1, 2, 3], taint_origin="source2")

        # Should be equal regardless of taint
        assert l1 == l2
        assert l1 == l3
        assert l2 == l3

        # Different contents should not be equal
        l4 = taint_wrap([1, 2, 4], taint_origin="source1")
        assert l1 != l4
