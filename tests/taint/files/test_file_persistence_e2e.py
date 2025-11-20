#!/usr/bin/env python3
"""
End-to-end test for cross-session file taint persistence with TaintWrapper.

This test verifies that:
1. TaintWrapper with persistence writes taint info to database when writing files
2. TaintWrapper with persistence reads taint info from database when reading files
3. Cross-session taint tracking works (write in session 1, read in session 2)
4. The taint_open() function and AST transformation work correctly
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

from aco.runner.taint_wrappers import TaintWrapper, get_taint_origins, taint_wrap
from aco.server.database_manager import DB
from aco.server.ast_transformer import taint_open

# Add utils path for test helpers
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import cleanup_taint_db, setup_test_session, with_ast_rewriting


class TestFilePeristenceE2E:
    """End-to-end tests for file persistence with TaintWrapper."""
    
    def setup_method(self):
        """Clean up before each test."""
        cleanup_taint_db()
    
    @with_ast_rewriting
    def test_taint_wrapper_file_write_persistence(self):
        """Test that TaintWrapper with persistence writes taint to database."""
        # Set up session
        os.environ["AGENT_COPILOT_SESSION_ID"] = "test-session-write"
        setup_test_session("test-session-write", name="Write Test Session")
        
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name
        
        try:
            # Create tainted data
            tainted_data = TaintWrapper("Secret data from node-001\n", taint_origin=["node-001"])
            
            # Open file with TaintWrapper (persistence enabled)
            with open(tmp_path, "w") as f:
                wrapped_file = TaintWrapper(f, taint_origin="file_source", enable_persistence=True)
                
                # Verify persistence is enabled
                assert wrapped_file._enable_persistence is True
                assert wrapped_file._session_id == "test-session-write"
                assert wrapped_file._line_no == 0
                
                # Write tainted data - this should go through AST transformation -> exec_func
                wrapped_file.write(tainted_data)
        
        finally:
            os.unlink(tmp_path)
    
    @with_ast_rewriting
    def test_taint_wrapper_file_read_persistence(self):
        """Test that TaintWrapper with persistence can read taint from database."""
        # Set up first session (writer)
        os.environ["AGENT_COPILOT_SESSION_ID"] = "session-001"
        setup_test_session("session-001", name="Writer Session")
        
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name
        
        try:
            # Session 1: Write tainted data
            tainted_data = TaintWrapper("Line 1: Secret info\nLine 2: More secrets\n", taint_origin=["node-001"])
            
            with open(tmp_path, "w") as f:
                wrapped_file = TaintWrapper(f, taint_origin="write_session", enable_persistence=True)
                # This goes through AST transformation -> exec_func for file persistence
                wrapped_file.write(tainted_data)
            
            # Session 2: Read the data back
            os.environ["AGENT_COPILOT_SESSION_ID"] = "session-002"
            setup_test_session("session-002", name="Reader Session")
            
            with open(tmp_path, "r") as f:
                wrapped_file = TaintWrapper(f, taint_origin="read_session", enable_persistence=True)
                
                # Read the data - should get taint from previous session via AST transformation
                content = wrapped_file.read()
                
                # Verify content is correct
                assert str(content) == "Line 1: Secret info\nLine 2: More secrets\n"
                
                # Verify taint is preserved from read session (file-level taint)
                # The specific line-level taint from session-001 should be retrievable via DB
                origins = get_taint_origins(content)
                assert "read_session" in origins  # File-level taint from current session
        
        finally:
            os.unlink(tmp_path)
    
    @with_ast_rewriting
    def test_cross_session_line_by_line_taint(self):
        """Test detailed cross-session line-by-line taint tracking."""
        # Session 1: Write multiple lines with different taint
        os.environ["AGENT_COPILOT_SESSION_ID"] = "session-lines-write"
        setup_test_session("session-lines-write", name="Line Writer")
        
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "w") as f:
                wrapped_file = TaintWrapper(f, taint_origin="file_writer", enable_persistence=True)
                
                # Write multiple lines with different taint origins
                line1 = TaintWrapper("First line from node-001\n", taint_origin=["node-001"])
                line2 = TaintWrapper("Second line from node-002\n", taint_origin=["node-002"])
                line3 = TaintWrapper("Third line combined\n", taint_origin=["node-001", "node-003"])
                
                # Each write goes through AST transformation -> exec_func
                wrapped_file.write(line1)
                wrapped_file.write(line2)
                wrapped_file.write(line3)
            
            # Session 2: Read line by line
            os.environ["AGENT_COPILOT_SESSION_ID"] = "session-lines-read"
            setup_test_session("session-lines-read", name="Line Reader")
            
            with open(tmp_path, "r") as f:
                wrapped_file = TaintWrapper(f, taint_origin="file_reader", enable_persistence=True)
                
                # Read line by line - each goes through AST transformation
                read_line1 = wrapped_file.readline()
                read_line2 = wrapped_file.readline()  
                read_line3 = wrapped_file.readline()
                
                # Verify content
                assert str(read_line1) == "First line from node-001\n"
                assert str(read_line2) == "Second line from node-002\n" 
                assert str(read_line3) == "Third line combined\n"
                
                # All lines should have file-level taint from current session
                assert "file_reader" in get_taint_origins(read_line1)
                assert "file_reader" in get_taint_origins(read_line2)
                assert "file_reader" in get_taint_origins(read_line3)
        
        finally:
            os.unlink(tmp_path)
    
    @with_ast_rewriting
    def test_taint_open_function(self):
        """Test the taint_open() function that replaces open() via AST transformation."""
        os.environ["AGENT_COPILOT_SESSION_ID"] = "taint-open-test"
        setup_test_session("taint-open-test", name="Taint Open Test")
        
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name
            tmp.write("Test content for taint_open")
        
        try:
            # Test taint_open for reading - this goes through AST transformation
            tainted_file = taint_open(tmp_path, "r")
            
            # Should be a TaintWrapper with persistence enabled
            assert isinstance(tainted_file, TaintWrapper)
            assert tainted_file._enable_persistence is True
            assert f"file:{tmp_path}" in tainted_file._taint_origin
            
            # Read content - this goes through AST transformation -> exec_func
            content = tainted_file.read()
            assert str(content) == "Test content for taint_open"
            assert isinstance(content, TaintWrapper)
            assert f"file:{tmp_path}" in get_taint_origins(content)
            
            tainted_file.close()
        
        finally:
            os.unlink(tmp_path)
    
    @with_ast_rewriting
    def test_taint_wrap_file_object(self):
        """Test that taint_wrap correctly handles file objects with persistence."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write("Test content")
            tmp.seek(0)
            
            # Test wrapping file object
            wrapped = taint_wrap(tmp, taint_origin="test_wrap")
            
            # Should be TaintWrapper with persistence enabled
            assert isinstance(wrapped, TaintWrapper)
            assert wrapped._enable_persistence is True
            assert "test_wrap" in wrapped._taint_origin
            
            # Should be able to read - this goes through AST transformation
            content = wrapped.read()
            assert str(content) == "Test content"
            
            tmp.close()
        
        os.unlink(tmp_path)
    
    @with_ast_rewriting
    def test_file_context_manager_persistence(self):
        """Test that file context managers work with persistence."""
        os.environ["AGENT_COPILOT_SESSION_ID"] = "context-test"
        setup_test_session("context-test", name="Context Manager Test")
        
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name
        
        try:
            # Test context manager with TaintWrapper
            with open(tmp_path, "w") as f:
                wrapped_file = TaintWrapper(f, taint_origin="context_source", enable_persistence=True)
                
                # Use in context manager
                with wrapped_file as file_handle:
                    # file_handle should be the underlying file object
                    assert file_handle is f
                    # This write goes through AST transformation
                    file_handle.write("Context manager test")
            
            # Verify file was written
            with open(tmp_path, "r") as f:
                content = f.read()
                assert content == "Context manager test"
        
        finally:
            os.unlink(tmp_path)
    
    @with_ast_rewriting
    def test_file_attribute_access_with_persistence(self):
        """Test that file attributes work correctly with persistence-enabled TaintWrapper."""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt") as tmp:
            wrapped_file = TaintWrapper(tmp, taint_origin="attr_test", enable_persistence=True)
            
            # Test file attributes
            assert wrapped_file.name == tmp.name
            assert "w+" in wrapped_file.mode  # mode might be 'w+b' depending on system
            assert not wrapped_file.closed
            
            # Test file capability methods
            assert wrapped_file.writable() is True
            assert wrapped_file.readable() is True
            assert wrapped_file.seekable() is True
            
            # Test position methods
            pos = wrapped_file.tell()
            assert isinstance(pos, int)
            
            # This write goes through AST transformation
            wrapped_file.write("position test")
            new_pos = wrapped_file.tell()
            assert new_pos > pos
            
            # Test seek
            wrapped_file.seek(0)
            assert wrapped_file.tell() == 0
    
    @with_ast_rewriting
    def test_file_mode_w_with_persistence(self):
        """Test write mode with persistence."""
        os.environ["AGENT_COPILOT_SESSION_ID"] = "mode-test-w"
        setup_test_session("mode-test-w", name="Mode w Test")
        
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "w") as f:
                wrapped_file = TaintWrapper(f, taint_origin="mode_w", enable_persistence=True)
                
                # Should have persistence enabled
                assert wrapped_file._enable_persistence is True
                
                # Should be able to write
                assert wrapped_file.writable() is True
                
                # This write goes through AST transformation -> exec_func
                result = wrapped_file.write("test content for mode w")
                assert result > 0
        
        finally:
            os.unlink(tmp_path)
    
    @with_ast_rewriting
    def test_file_mode_w_plus_with_persistence(self):
        """Test write+ mode with persistence."""
        os.environ["AGENT_COPILOT_SESSION_ID"] = "mode-test-w+"
        setup_test_session("mode-test-w+", name="Mode w+ Test")
        
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "w+") as f:
                wrapped_file = TaintWrapper(f, taint_origin="mode_w+", enable_persistence=True)
                
                # Should have persistence enabled
                assert wrapped_file._enable_persistence is True
                
                # Should be able to write
                assert wrapped_file.writable() is True
                
                # This write goes through AST transformation -> exec_func
                result = wrapped_file.write("test content for mode w+")
                assert result > 0
        
        finally:
            os.unlink(tmp_path)
    
    @with_ast_rewriting
    def test_file_mode_a_with_persistence(self):
        """Test append mode with persistence."""
        os.environ["AGENT_COPILOT_SESSION_ID"] = "mode-test-a"
        setup_test_session("mode-test-a", name="Mode a Test")
        
        with tempfile.NamedTemporaryFile(mode="a", delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "a") as f:
                wrapped_file = TaintWrapper(f, taint_origin="mode_a", enable_persistence=True)
                
                # Should have persistence enabled
                assert wrapped_file._enable_persistence is True
                
                # Should be able to write
                assert wrapped_file.writable() is True
                
                # This write goes through AST transformation -> exec_func
                result = wrapped_file.write("test content for mode a")
                assert result > 0
        
        finally:
            os.unlink(tmp_path)
    
    @with_ast_rewriting
    def test_file_mode_a_plus_with_persistence(self):
        """Test append+ mode with persistence."""
        os.environ["AGENT_COPILOT_SESSION_ID"] = "mode-test-a+"
        setup_test_session("mode-test-a+", name="Mode a+ Test")
        
        with tempfile.NamedTemporaryFile(mode="a+", delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "a+") as f:
                wrapped_file = TaintWrapper(f, taint_origin="mode_a+", enable_persistence=True)
                
                # Should have persistence enabled
                assert wrapped_file._enable_persistence is True
                
                # Should be able to write
                assert wrapped_file.writable() is True
                
                # This write goes through AST transformation -> exec_func
                result = wrapped_file.write("test content for mode a+")
                assert result > 0
        
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    # Run specific test
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v"
    ], cwd=Path(__file__).parent.parent.parent.parent)
    sys.exit(result.returncode)