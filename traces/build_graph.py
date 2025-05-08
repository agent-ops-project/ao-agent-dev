import networkx as nx


class CallGraph:
    """
    Dependency tree of LLM calls, with input and output nodes.
    E.g.: input <-- LLM_call_1 <-- LLM_call_2 <-- output

    CallGraph also contains eval data of graph nodes (e.g., pass/fail 
    for unit tests).
    """

    def __init__(self):
        self.lineage_graph = None
        pass


    def from_codegen_log(self):
        """
        Parses out the call lineage of how functions are generated. 
        For each test, it also parses out what functions that test 
        called.
        """
        # TODO: Build lineage.
        
        # TODO: Parse test log.
        self.passed_test_calls = {}
        self.failed_test_calls = {}
        pass