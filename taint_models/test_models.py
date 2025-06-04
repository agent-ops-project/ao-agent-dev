"""
Implementation of test source and sink functions for taint analysis.
"""

def __test_source():
    """Test source that returns a tainted value."""
    return "tainted_data"

def __test_sink(arg):
    """Test sink that receives a potentially tainted value."""
    pass 