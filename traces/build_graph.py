from collections import defaultdict
from difflib import SequenceMatcher
from enum import Enum
import json
import os
import re
import time
import networkx as nx
import matplotlib.pyplot as plt
import concurrent.futures
from main import setup_logging

logger = setup_logging()


class GraphType(Enum):
    CODE_GEN = "code_gen"
    EMPTY = "empty"


class CallGraph:
    """
    Dependency tree of LLM calls, with input and output nodes.
    E.g.: input <-- LLM_call_1 <-- LLM_call_2 <-- output

    CallGraph also contains eval data of graph nodes (e.g., pass/fail 
    for unit tests).
    """

    def __init__(self):
        self.G = None
        self.graph_type = GraphType.EMPTY

        self.terminal_nodes = []

        # Attributes for code-gen.
        # TODO


    def from_codegen_log(self, trace_path):
        """
        Parses out the call lineage of how functions are generated. 
        For each test, it also parses out what functions that test 
        called.

        `trace_path` can be an exact path, or:
        - 'fundraising_crm latest'
        """
        self.graph_type = GraphType.CODE_GEN
        self.G = nx.Graph(directed=True)

        # 1. If path doesn't exist, assume it's a trace name.
        if not os.path.exists(trace_path):
            trace_path = get_trace_path(trace_path)
        
        # 2. Read file and init nodes.
        start = time.time()
        with open(trace_path, "r") as f:
            llm_calls = f.readlines()
        
        # Node 0 is the input spec.
        self.G.add_node(0, 
                system_mg="N/A",
                llm_in="N/A", 
                llm_out="N/A", 
                timestamp="N/A", 
                cache_key="root_spec_0_user")

        # Add nodes from trace file.
        for id, llm_call in enumerate(llm_calls):
            call_dict = json.loads(llm_call)
            self.G.add_node(id+1, 
                            system_mg=call_dict["system_msg"],
                            llm_in=call_dict["prompt"], 
                            llm_out=call_dict["output"], 
                            timestamp=call_dict["timestamp"], 
                            cache_key=call_dict["cache_key"])
        logger.info(f"Insert nodes: {time.time() - start}")

        # 3. Insert edges (build dependency lineage).
        start = time.time()
        self._insert_edges_hardcoded()

        self.terminal_nodes = []
        for node in self.G.nodes:
            if self.G.degree(node) == 1:
                self.terminal_nodes.append(node)
        logger.info(f"Insert edges: {time.time() - start}")


        # TODO: Cache graph.

        # 4. Parse test log (TODO)
        start = time.time()
        self.passed_test_calls = {}
        self.failed_test_calls = {}
        logger.info(f"Parse test log: {time.time() - start}")


    def get_test_lineage(self):
        # Make subgraph for test's lineage.
        test_lineage = nx.Graph(directed=True)

        # Test entry example:
        # fundraising_crm_tree_src.backend_services.data_models.Task_0_sonnet3.7-nothink

        # Get terminal relevant nodes.
        "test should just be the path as is?"
        " -> map"

        "for all terminal nodes, check which ones match. You need to consider that some terminal nodes are for classes and others not"
        # Get leave nodes -> called fn in csv to node.
        # Nimm den closest match und dann die hoechste nummer.
        # Jede gecallte function is File.Class
        # 1. File.Class if available, else File
        # 2. Groesste nummer davon 

        # Do DFS and insert nodes

        pass


    def visualize(self):
        # Categorize nodes for plotting.
        root_node = [0]
        normal_nodes = []
        exit_nodes = []
        for node in self.G.nodes:
            if self.G.degree(node) == 0:
                # TODO: There are "stray test reviews" (i.e., review -> {missing fix} -> review).
                # We will just pretend they aren't there.
                # print("Ignoring", self.G.nodes[node]["cache_key"])
                continue
            elif self.G.degree(node) == 1:
                exit_nodes.append(node)
            else:
                normal_nodes.append(node)

        # Plotting layout (spread nodes out)
        pos = nx.spring_layout(self.G,
                            k=0.06,
                            iterations=50,
                            seed=42)
        
        # Normal nodes.
        nx.draw_networkx_nodes(self.G,
                            pos,
                            nodelist=normal_nodes,
                            node_size=50,
                            label="LLM calls")

        # Root node.
        nx.draw_networkx_nodes(self.G,
                            pos,
                            nodelist=root_node,
                            node_size=150,
                            node_color='red',
                            label="User's design doc")
        
        # Terminal nodes.
        nx.draw_networkx_nodes(self.G,
                            pos,
                            nodelist=exit_nodes,
                            node_size=70,
                            node_color="limegreen",
                            label="Terminal LLM call")

        nx.draw_networkx_edges(self.G, pos)
        plt.legend(loc="lower right")
        plt.show()


    def _insert_edges_lcs(self, match_threshold=100):
        for n_in in self.G.nodes:
            longest = 0
            n_out_longest = -1
            for n_out in self.G.nodes:
                in_text = self.G.nodes[n_in]["llm_in"]
                out_text = self.G.nodes[n_out]["llm_out"]

                # TODO: Just assume there's only one or 0 edges. 
                length = find_longest_match(in_text, out_text)
                if length > longest:
                    longest = length
                    n_out_longest = n_out

            if longest > match_threshold:
                self.G.add_edge(n_in, n_out_longest)


    def _insert_edges_lcs_parallel(self, match_threshold=100):
        # 1. Determine which edges to add in parallel.
        node_attrs = {node: {"llm_in": self.G.nodes[node].get("llm_in", ""),
                            "llm_out": self.G.nodes[node].get("llm_out", "")}
                    for node in self.G.nodes}

        args_list = [(n1, n2, node_attrs[n1], node_attrs[n2], match_threshold)
                    for n1 in node_attrs for n2 in node_attrs]
        with concurrent.futures.ProcessPoolExecutor() as executor:
            results = executor.map(compare_nodes, args_list)

        # 2. Add edges from results
        for result in results:
            if result:
                n_in, n_out, score = result
                self.G.add_edge(n_in, n_out, score=score)


    def _insert_edges_hardcoded(self):
        # 1. Connect code transpile nodes.
        self._connect_adjacent_cache_keys(node_type="file_planner_analysis", dependent_node_type="file_planner_iterate")
        self._connect_adjacent_cache_keys(node_type="file_planner_iterate", dependent_node_type="file_transpiler_analysis")
        self._connect_adjacent_cache_keys(node_type="file_transpiler_analysis", dependent_node_type="file_transpiler_transpilation")
        self._connect_adjacent_cache_keys(node_type="file_transpiler_transpilation", dependent_node_type=None)

        # 2. Connect test transpile nodes.
        self._connect_adjacent_cache_keys(node_type="class_test_spec_gen_unit", dependent_node_type=None)
        self._connect_adjacent_cache_keys(node_type="class_test_spec_gen_integration", dependent_node_type=None)
        self._connect_adjacent_cache_keys(node_type="method_test_transpiling_gen", dependent_node_type="method_test_transpiling_review")
        self._interleave_cache_keys(node_type="method_test_transpiling_review", dependent_node_type="method_test_transpiling_fix")

        # self._connect_node_types(node_type="class_test_spec_gen_unit", dependent_node_type="class_test_spec_gen_integration")
        self._connect_node_types(node_type="class_test_spec_gen_unit", dependent_node_type="method_test_transpiling_gen")
        self._connect_node_types(node_type="class_test_spec_gen_integration", dependent_node_type="method_test_transpiling_gen")
        self._connect_node_types(node_type="method_test_transpiling_review", dependent_node_type="file_planner_analysis")

        # 3. Connect to root spec.
        self._connect_to_root(dependent_node_type="file_planner_analysis")
        self._connect_to_root(dependent_node_type="class_test_spec_gen_unit")
        self._connect_to_root(dependent_node_type="class_test_spec_gen_integration")


    def _group_nodes_by_cache_key(self, node_type):
        """
        Groups nodes by (middle, suffix): their numeric index and node_id.
        Returns dict { (middle, suffix): [(x, node_id), ...] }
        """
        # Regex: match node_type prefix, capture middle, number, and suffix
        pattern = re.compile(rf"^{re.escape(node_type)}_(.*?_)(\d+)(_.*)$")
        grouped = defaultdict(list)

        for node_id in self.G.nodes:
            cache_key = self.G.nodes[node_id].get("cache_key", "")
            match = pattern.match(cache_key)
            if not match:
                continue

            middle, num_str, suffix = match.groups()
            grouped[(middle, suffix)].append((int(num_str), node_id))

        return grouped


    def _connect_adjacent_cache_keys(self, node_type, dependent_node_type=None):
        """
        Connects nodes of node_type by adding edges x → x-1,
        and if dependent_node_type is provided, adds an edge from the first
        node of dependent_node_type to the last node of node_type,
        for each shared (middle, suffix) group.
        """
        # Intra-type connections
        primary_map = self._group_nodes_by_cache_key(node_type)
        for key, entries in primary_map.items():
            entries.sort()
            nodes_by_x = {x: nid for x, nid in entries}
            for x, node_id in nodes_by_x.items():
                prev_x = x - 1
                if prev_x in nodes_by_x:
                    self.G.add_edge(node_id, nodes_by_x[prev_x])

        # Cross-type connection (first dependent → last primary)
        if dependent_node_type:
            self._connect_node_types(node_type, dependent_node_type)


    def _interleave_cache_keys(self, node_type, dependent_node_type):
        """
        Connects two node types in an interleaved zig-zag pattern:
        For each version x in their shared groups:
          dependent[x] → node_type[x]
          node_type[x+1] → dependent[x]
          dependent[x+1] → node_type[x+1]
        """
        map_dep = self._group_nodes_by_cache_key(dependent_node_type)
        map_main = self._group_nodes_by_cache_key(node_type)

        # Only process groups present in both types
        for key in map_dep.keys() & map_main.keys():
            dep_entries = {x: nid for x, nid in map_dep[key]}
            main_entries = {x: nid for x, nid in map_main[key]}
            all_versions = sorted(set(dep_entries) | set(main_entries))

            for x in all_versions:
                dep_cur = dep_entries.get(x)
                main_cur = main_entries.get(x)
                dep_next = dep_entries.get(x + 1)
                main_next = main_entries.get(x + 1)

                # dependent[x] → main[x]
                if dep_cur and main_cur:
                    self.G.add_edge(dep_cur, main_cur)
                # main[x+1] → dependent[x]
                if main_next and dep_cur:
                    self.G.add_edge(main_next, dep_cur)
                # dependent[x+1] → main[x+1]
                if dep_next and main_next:
                    self.G.add_edge(dep_next, main_next)


    def _connect_node_types(self, node_type, dependent_node_type):
        """
        For each shared (middle, suffix) group between node_type and dependent_node_type,
        adds an edge from the first node of dependent_node_type to the last node of node_type.
        """
        primary_map = self._group_nodes_by_cache_key(node_type)
        dep_map = self._group_nodes_by_cache_key(dependent_node_type)

        # For keys present in both maps, connect first dependent → last primary
        for key in primary_map.keys() & dep_map.keys():
            entries = primary_map[key]
            dep_entries = dep_map[key]
            _, last_primary = max(entries)
            _, first_dep = min(dep_entries)
            self.G.add_edge(first_dep, last_primary)


    def _connect_to_root(self, dependent_node_type, root_id=0):
        """
        For each shared (middle, suffix) group between node_type and dependent_node_type,
        adds an edge from the first node of dependent_node_type to the last node of node_type.
        """
        dep_map = self._group_nodes_by_cache_key(dependent_node_type)

        # For keys present in both maps, connect first dependent → last primary
        for key in dep_map.keys():
            dep_entries = dep_map[key]
            _, first_dep = min(dep_entries)
            self.G.add_edge(first_dep, root_id)

# =========================================================
# Helpers
# =========================================================
def compare_nodes(args):
    n_in, n_out, attrs_in, attrs_out, threshold = args
    if n_in == n_out:
        return None
    score = find_longest_match(attrs_in["llm_in"], attrs_out["llm_out"])
    if score > threshold:
        return (n_in, n_out, score)
    return None


def get_trace_path(trace_name):
    """
    Possible trace_names: 
     - 'fundraising_crm latest'
    """
    cur_dir = os.path.dirname(__file__)
    if trace_name == 'fundraising_crm latest':
        prefix = "fundraising_crm_"
        code_gen_dir = os.path.join(cur_dir, "code_gen")

        most_recent = max([
            d for d in os.listdir(code_gen_dir)
            if os.path.isdir(os.path.join(code_gen_dir, d)) and re.match(rf"{prefix}\d{{2}}_\d{{2}}$", d)
        ])

        assert most_recent, "No matching trace dir present"
        fundraising_crm_dir = os.path.join(cur_dir, "code_gen", most_recent, "fundraising_crm_traj.jsonl")
        return fundraising_crm_dir
    else:
        raise ValueError(f"Trace name '{trace_name}' is not a recognized.")


def normalize_tokens(text):
    lines = [ln.lstrip() for ln in text.splitlines()]
    flat = " ".join(lines).lower().strip()
    return re.findall(r"\w+|\S", flat)


def find_longest_match(string_a, string_b):
    a_tok = normalize_tokens(string_a)
    b_tok = normalize_tokens(string_b)
    sm = SequenceMatcher(None, a_tok, b_tok)

    a = [block.size for block in sm.get_matching_blocks()]
    b = [block for block in sm.get_matching_blocks()]

    # a_str = a_tok[b[4].a:b[4].a+100]
    # b_str = b_tok[b[4].b:b[4].b+100]

    max_match = max([block.size for block in sm.get_matching_blocks()])
    # if max_match > 100:
    #     print()
    return max_match


if __name__ == "__main__":
    cg = CallGraph()
    cg.from_codegen_log("fundraising_crm latest")
    cg.visualize()
