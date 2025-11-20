"""Unit tests for TaintWrapper class."""

import pytest
import io
import tempfile
import os

from aco.runner.taint_wrappers import TaintWrapper, get_taint_origins, is_tainted, untaint_if_needed
from ...utils import cleanup_taint_db


class TestTaintWrapper:
    """Test suite for unified TaintWrapper class."""

    def setup_method(self):
        """Clean up taint database before each test method"""
        cleanup_taint_db()

    def test_creation(self):
        """Test TaintWrapper creation with various objects and taint origins."""
        # Test with no taint
        w1 = TaintWrapper("hello")
        assert w1.obj == "hello"
        assert w1._taint_origin == []
        assert not is_tainted(w1)

        # Test with single string taint
        w2 = TaintWrapper("world", taint_origin="source1")
        assert w2.obj == "world"
        assert w2._taint_origin == ["source1"]
        assert is_tainted(w2)

        # Test with single int taint
        w3 = TaintWrapper(42, taint_origin="source2")
        assert w3.obj == 42
        assert w3._taint_origin == ["source2"]
        assert is_tainted(w3)

        # Test with list taint
        w4 = TaintWrapper([1, 2, 3], taint_origin=["source1", "source2"])
        assert w4.obj == [1, 2, 3]
        assert w4._taint_origin == ["source1", "source2"]
        assert is_tainted(w4)

        # Test invalid taint origin type
        with pytest.raises(TypeError):
            TaintWrapper("invalid", taint_origin={})

    def test_string_operations(self):
        """Test string operations with TaintWrapper."""
        s1 = TaintWrapper("hello", taint_origin="source1")
        s2 = TaintWrapper(" world", taint_origin="source2")

        # String representation
        assert str(s1) == "hello"
        assert str(s2) == " world"

        # Test that string operations work through AST transformation
        # (Note: actual operation wrapping tested separately in integration tests)
        assert s1.obj == "hello"
        assert s2.obj == " world"

    def test_numeric_operations(self):
        """Test numeric operations with TaintWrapper."""
        n1 = TaintWrapper(10, taint_origin="num1")
        n2 = TaintWrapper(20, taint_origin="num2")

        # Numeric representation
        assert n1.obj == 10
        assert n2.obj == 20

        # Boolean conversion
        assert bool(n1) is True
        assert bool(TaintWrapper(0)) is False

    def test_collection_operations(self):
        """Test collection operations with TaintWrapper."""
        # List operations
        lst = TaintWrapper([1, 2, 3], taint_origin="list_source")
        assert lst.obj == [1, 2, 3]
        assert len(lst.obj) == 3

        # Dict operations
        dct = TaintWrapper({"key": "value"}, taint_origin="dict_source")
        assert dct.obj == {"key": "value"}
        assert "key" in dct.obj

        # Iteration
        iterable_list = TaintWrapper([1, 2, 3], taint_origin="iter_source")
        items = list(iter(iterable_list))
        assert items == [1, 2, 3]

    def test_method_calls(self):
        """Test method calls on wrapped objects."""
        # String methods
        s = TaintWrapper("hello", taint_origin="string_test")
        
        # Methods should be accessible through partial binding
        upper_method = s.upper
        assert callable(upper_method)
        
        # List methods
        lst = TaintWrapper([1, 2], taint_origin="list_test")
        append_method = lst.append
        assert callable(append_method)

    def test_attribute_access(self):
        """Test attribute access on wrapped objects."""
        class TestObj:
            def __init__(self):
                self.value = 42
                self.name = "test"
        
        obj = TestObj()
        wrapped = TaintWrapper(obj, taint_origin="attr_test")
        
        # Attribute access should return tainted values
        value = wrapped.value
        assert isinstance(value, TaintWrapper)
        assert value.obj == 42
        assert get_taint_origins(value) == ["attr_test"]

    def test_file_persistence(self):
        """Test file operations with persistence enabled."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Test file wrapper with persistence
            with open(tmp_path, "w") as f:
                wrapped_file = TaintWrapper(f, taint_origin="file_test", enable_persistence=True)
                
                # Check persistence attributes are set
                assert wrapped_file._enable_persistence is True
                assert wrapped_file._line_no == 0
                assert hasattr(wrapped_file, "_session_id")
                
                # File operations should work
                assert wrapped_file.writable()

        finally:
            os.unlink(tmp_path)

    def test_taint_origins_extraction(self):
        """Test taint origins extraction from nested structures."""
        # Simple wrapper
        w1 = TaintWrapper("test", taint_origin=["origin1"])
        origins = get_taint_origins(w1)
        assert origins == ["origin1"]

        # Nested structures
        nested = {
            "key1": TaintWrapper("value1", taint_origin=["nested1"]),
            "key2": [TaintWrapper(42, taint_origin=["nested2"]), "clean"]
        }
        all_origins = get_taint_origins(nested)
        assert set(all_origins) == {"nested1", "nested2"}

    def test_untaint_functionality(self):
        """Test untainting wrapped objects."""
        # Simple object
        wrapped_str = TaintWrapper("hello", taint_origin=["test"])
        untainted = untaint_if_needed(wrapped_str)
        assert untainted == "hello"
        assert not hasattr(untainted, "_taint_origin")

        # Nested structure
        nested = {
            "tainted": TaintWrapper("secret", taint_origin=["source"]),
            "clean": "public"
        }
        untainted_nested = untaint_if_needed(nested)
        assert untainted_nested["tainted"] == "secret"
        assert untainted_nested["clean"] == "public"
        assert not hasattr(untainted_nested["tainted"], "_taint_origin")

    def test_context_manager(self):
        """Test context manager protocol delegation."""
        with tempfile.NamedTemporaryFile(mode="w") as tmp:
            wrapped_file = TaintWrapper(tmp, taint_origin="context_test")
            
            # Should support context manager protocol
            with wrapped_file as f:
                assert f is tmp  # Delegation to underlying object

    def test_callable_objects(self):
        """Test wrapping callable objects."""
        def test_func(x):
            return x * 2
        
        wrapped_func = TaintWrapper(test_func, taint_origin="func_test")
        
        # Should be callable
        assert callable(wrapped_func)
        
        # Calling should work and propagate taint
        result = wrapped_func(5)
        assert isinstance(result, TaintWrapper)
        assert result.obj == 10
        assert get_taint_origins(result) == ["func_test"]

    def test_repr_and_str(self):
        """Test string representations."""
        wrapped = TaintWrapper("test", taint_origin=["repr_test"])
        
        # String conversion
        assert str(wrapped) == "test"
        
        # Repr should show wrapper info
        repr_str = repr(wrapped)
        assert "TaintWrapper" in repr_str
        assert "repr_test" in repr_str

    def test_hash_and_equality(self):
        """Test hash and equality operations."""
        wrapped1 = TaintWrapper("test", taint_origin=["hash_test"])
        wrapped2 = TaintWrapper("test", taint_origin=["hash_test"])
        
        # Hash should delegate to wrapped object
        assert hash(wrapped1) == hash("test")
        assert hash(wrapped1) == hash(wrapped2)

    def test_copy_operations(self):
        """Test copy and pickle operations."""
        import copy
        
        wrapped = TaintWrapper([1, 2, 3], taint_origin=["copy_test"])
        
        # Shallow copy should return unwrapped object
        copied = copy.copy(wrapped)
        assert copied == [1, 2, 3]
        assert not hasattr(copied, "_taint_origin")
        
        # Deep copy should also return unwrapped object
        deep_copied = copy.deepcopy(wrapped)
        assert deep_copied == [1, 2, 3]
        assert not hasattr(deep_copied, "_taint_origin")

    def test_class_transparency(self):
        """Test that wrapper appears as wrapped object's class."""
        wrapped_str = TaintWrapper("test", taint_origin=["class_test"])
        wrapped_list = TaintWrapper([1, 2, 3], taint_origin=["class_test"])
        
        # Class should appear as wrapped object's class
        assert wrapped_str.__class__ == str
        assert wrapped_list.__class__ == list

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Empty taint origin
        w1 = TaintWrapper("test", taint_origin=[])
        assert not is_tainted(w1)
        
        # None taint origin
        w2 = TaintWrapper("test", taint_origin=None)
        assert not is_tainted(w2)
        
        # Wrapping None
        w3 = TaintWrapper(None, taint_origin=["null_test"])
        assert w3.obj is None
        assert is_tainted(w3)
        
        # Wrapping already wrapped object
        inner = TaintWrapper("inner", taint_origin=["inner"])
        outer = TaintWrapper(inner, taint_origin=["outer"])
        assert outer.obj is inner
        assert get_taint_origins(outer) == ["outer"]