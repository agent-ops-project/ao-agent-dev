from prompts import *
import json
from amadou_parse_tags import parse_out_tag

# TODO: Automatically from lineage graph.
# TODO: Bug with tags not present.

class PromptConstructor:

    def __init__(self, call_file):
        self.llm_call_dicts = None
        self.parse_calls(call_file)


    # def pretty_display(raw_string):
    #     """
    #     Takes string with escaped characters and formats it to respect the escaped characters.
    #     """
    #     decoded = raw_string.encode().decode('unicode_escape')
    #     with open("hello.txt", "w") as f:
    #         f.write(decoded)


    def pretty_display(self, raw_string: str):
        """
        Takes string with escaped characters and formats it to respect the escaped characters.
        """
        decoded = raw_string.encode().decode('unicode_escape')
        return decoded


    def get_entry(self, cache_key, entry_type):
        for d in self.llm_call_dicts:
            if cache_key == d["cache_key"]:
                return self.pretty_display(d[entry_type])


    def get_response(self, cache_key, tag, entry_type="output"):
        # try:
        full_entry = self.get_entry(cache_key, entry_type)
        relevant_part = parse_out_tag(full_entry, tag) 
        return relevant_part
        # except:
        # print(f"Tag {tag} not present in {cache_key}!!!")
        return None


    def get_key(self, relevant_keys, categ, iter):
        # TODO: Assumes only one file present in trace.
        for k in relevant_keys:
            if categ in k and f"_{iter}_" in k:
                return k
        return None


    def parse_calls(self, input_file):
        # Read log of llm_calls.
        with open(input_file, "r") as f:
            lines = f.readlines()
        self.llm_call_dicts = [json.loads(l) for l in lines]

        # Map agent (e.g., transpile) to all llm_calls from that agent.
        # all_cache_keys = [entry["cache_key"] for entry in self.llm_call_dicts]
        # relevant_key_categs = [
        #     "file_planner_analysis",
        #     "file_planner_iterate",
        #     "file_transpiler_analysis",
        #     "file_transpiler_transpilation"
        # ]
        # self.keys_in_categ = {}
        # for categ in relevant_key_categs:
        #     self.keys_in_categ[categ] = [call for call in all_cache_keys if categ in call]


    def after_the_fact_prompt(self, relevant_cache_keys: list[str], output_file: str):
        # TODO: Only supports calls for one module.
        """
        `relevant_cache_keys`: From all LLM calls in `self.llm_call_dicts`,
        which cache keys should be used to create the prompt?

        `output_file`: Prompt is written to a file.
        """
        f = open(output_file, "w")
        step_ctr = 1

        # Add planner analysis.
        cache_key = self.get_key(relevant_cache_keys, "file_planner_analysis", 0)
        analysis = self.get_response(cache_key, "analysis", "output")
        prompt = instructions.format(analysis=analysis)
        f.write(prompt + "\n")
        step_ctr += 1

        # Add planning.
        plan_itr = 0
        while (cache_key := self.get_key(relevant_cache_keys, "file_planner_iterate", plan_itr)):

            print("plan", plan_itr, output_file)
            plan = self.get_response(cache_key, "next_plan", "output")
            analysis = self.get_response(cache_key, "iteration_state", "output")
            prompt = plan_prompt.format(iter=step_ctr, plan=plan, analysis=analysis)
            f.write(prompt + "\n")

            step_ctr += 1
            plan_itr += 2

        # Add implementation.
        # NOTE: Every second 'file_transpiler_transpilation' is review
        # TODO: This sometimes fails bc there's no <review> tag. Look into this
        impl_iter = 0
        while (cache_key_impl := self.get_key(relevant_cache_keys, "file_transpiler_transpilation", impl_iter)) \
            and (cache_key_review := self.get_key(relevant_cache_keys, "file_transpiler_transpilation", impl_iter+1)):
        
            print("impl", impl_iter, output_file)

            impl = self.get_response(cache_key_impl, "transpilation", "output")
            review = self.get_response(cache_key_review, "review", "output")
            prompt = impl_prompt.format(iter=step_ctr, implementation=impl, review=review)
            f.write(prompt + "\n")

            step_ctr += 1
            impl_iter += 2

        # Final.
        f.write(test_prompt)
        f.close()


    def rate_correctness_prompt(self, relevant_cache_keys: list[str], output_file: str):
        # TODO: Only supports calls for one module.
        """
        `relevant_cache_keys`: From all LLM calls in `self.llm_call_dicts`,
        which cache keys should be used to create the prompt?

        `output_file`: Prompt is written to a file.
        """
        f = open(output_file, "w")
        step_ctr = 1

        # Add planner analysis.
        cache_key = self.get_key(relevant_cache_keys, "file_planner_analysis", 0)
        analysis = self.get_response(cache_key, "analysis", "output")
        prompt = instructions.format(analysis=analysis)
        f.write(prompt + "\n")
        step_ctr += 1

        # Add planning.
        plan_itr = 0
        while (cache_key := self.get_key(relevant_cache_keys, "file_planner_iterate", plan_itr)):

            print("plan", plan_itr, output_file)
            plan = self.get_response(cache_key, "next_plan", "output")
            analysis = self.get_response(cache_key, "iteration_state", "output")
            prompt = plan_prompt.format(iter=step_ctr, plan=plan, analysis=analysis)
            f.write(prompt + "\n")

            step_ctr += 1
            plan_itr += 2

        # Add implementation.
        # NOTE: Every second 'file_transpiler_transpilation' is review
        # TODO: This sometimes fails bc there's no <review> tag. Look into this
        impl_iter = 0
        while (cache_key_impl := self.get_key(relevant_cache_keys, "file_transpiler_transpilation", impl_iter)) \
            and (cache_key_review := self.get_key(relevant_cache_keys, "file_transpiler_transpilation", impl_iter+1)):
        
            print("impl", impl_iter, output_file)

            impl = self.get_response(cache_key_impl, "transpilation", "output")
            review = self.get_response(cache_key_review, "review", "output")
            prompt = impl_prompt.format(iter=step_ctr, implementation=impl, review=review)
            f.write(prompt + "\n")

            step_ctr += 1
            impl_iter += 2

        # Final.
        f.write(test_prompt)
        f.close()


    def rate_corr_prompt(self, relevant_cache_keys: list[str], output_file: str):
        # TODO: Only supports calls for one module.
        """
        `relevant_cache_keys`: From all LLM calls in `self.llm_call_dicts`,
        which cache keys should be used to create the prompt?

        `output_file`: Prompt is written to a file.
        """
        f = open(output_file, "w")
        step_ctr = 1

        # Add planner analysis.
        # cache_key = self.get_key(relevant_cache_keys, "file_planner_analysis", 0)
        # analysis = self.get_response(cache_key, "analysis", "output")
        # prompt = instructions.format(analysis=analysis)
        # f.write(prompt + "\n")
        # step_ctr += 1

        # Add planning.
        plan_itr = 0
        while (cache_key := self.get_key(relevant_cache_keys, "file_planner_iterate", plan_itr)):

            print("plan", plan_itr, output_file)
            plan = self.get_response(cache_key, "next_plan", "output")
            analysis = self.get_response(cache_key, "iteration_state", "output")
            prompt = rate_correctness_prompt.format(output=plan, review=analysis)
            f.write(prompt + "\n")

            step_ctr += 1
            plan_itr += 2
            f.write("*"*20 + "\n")

        # Add implementation.
        # NOTE: Every second 'file_transpiler_transpilation' is review
        # TODO: This sometimes fails bc there's no <review> tag. Look into this
        impl_iter = 0
        while (cache_key_impl := self.get_key(relevant_cache_keys, "file_transpiler_transpilation", impl_iter)) \
            and (cache_key_review := self.get_key(relevant_cache_keys, "file_transpiler_transpilation", impl_iter+1)):
        
            print("impl", impl_iter)

            impl = self.get_response(cache_key_impl, "transpilation", "output")
            review = self.get_response(cache_key_review, "review", "output")
            prompt = rate_correctness_prompt.format(output=impl, review=review)
            f.write(prompt + "\n")

            f.write("*"*20 + "\n")
            step_ctr += 1
            impl_iter += 2

        # Final.
        # f.write(test_prompt)
        f.close()


if __name__ == "__main__":

    path_to_jsonl = "/Users/ferdi/Documents/agent-copilot/traces/code_gen/fundraising_crm_05_09/fundraising_crm_traj.jsonl"
    pc = PromptConstructor(path_to_jsonl)

    gen_entries = ['class_test_spec_gen_unit_fundraising_crm_tree_src.database.db_operations.PostgresOperations_0_sonnet3.7-nothink', 'class_test_spec_gen_integration_fundraising_crm_tree_src.database.db_operations.PostgresOperations_0_sonnet3.7-nothink', 'method_test_transpiling_gen_fundraising_crm_tree_src.database.db_operations.PostgresOperations_0_sonnet3.7-nothink', 'method_test_transpiling_gen_fundraising_crm_tree_src.database.db_operations.PostgresOperations_1_sonnet3.7-nothink', 'method_test_transpiling_review_fundraising_crm_tree_src.database.db_operations.PostgresOperations_0_sonnet3.7-nothink', 'method_test_transpiling_fix_fundraising_crm_tree_src.database.db_operations.PostgresOperations_0_sonnet3.7-nothink', 'method_test_transpiling_review_fundraising_crm_tree_src.database.db_operations.PostgresOperations_1_sonnet3.7-nothink', 'method_test_transpiling_fix_fundraising_crm_tree_src.database.db_operations.PostgresOperations_1_sonnet3.7-nothink', 'method_test_transpiling_review_fundraising_crm_tree_src.database.db_operations.PostgresOperations_2_sonnet3.7-nothink', 'method_test_transpiling_review_fundraising_crm_tree_src.database.db_operations.PostgresOperations_3_sonnet3.7-nothink', 'method_test_transpiling_fix_fundraising_crm_tree_src.database.db_operations.PostgresOperations_2_sonnet3.7-nothink', 'method_test_transpiling_review_fundraising_crm_tree_src.database.db_operations.PostgresOperations_4_sonnet3.7-nothink', 'method_test_transpiling_fix_fundraising_crm_tree_src.database.db_operations.PostgresOperations_3_sonnet3.7-nothink', 'method_test_transpiling_review_fundraising_crm_tree_src.database.db_operations.PostgresOperations_5_sonnet3.7-nothink', 'method_test_transpiling_fix_fundraising_crm_tree_src.database.db_operations.PostgresOperations_4_sonnet3.7-nothink', 'method_test_transpiling_review_fundraising_crm_tree_src.database.db_operations.PostgresOperations_6_sonnet3.7-nothink', 'method_test_transpiling_fix_fundraising_crm_tree_src.database.db_operations.PostgresOperations_5_sonnet3.7-nothink', 'file_planner_analysis_fundraising_crm_tree_src.database.db_operations_0_sonnet3.7-nothink', 'file_planner_analysis_fundraising_crm_tree_src.database.db_operations_1_sonnet3.7-nothink', 'file_planner_iterate_fundraising_crm_tree_src.database.db_operations_0_sonnet3.7-nothink', 'file_planner_iterate_fundraising_crm_tree_src.database.db_operations_1_sonnet3.7-nothink', 'file_planner_iterate_fundraising_crm_tree_src.database.db_operations_2_sonnet3.7-nothink', 'file_planner_iterate_fundraising_crm_tree_src.database.db_operations_3_sonnet3.7-nothink', 'file_planner_iterate_fundraising_crm_tree_src.database.db_operations_4_sonnet3.7-nothink', 'file_planner_iterate_fundraising_crm_tree_src.database.db_operations_5_sonnet3.7-nothink', 'file_transpiler_analysis_fundraising_crm_tree_src.database.db_operations_0_sonnet3.7-nothink', 'file_transpiler_analysis_fundraising_crm_tree_src.database.db_operations_1_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_0_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_1_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_2_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_3_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_4_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_5_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_6_sonnet3.7-nothink', 'file_transpiler_analysis_fundraising_crm_tree_src.database.db_operations_2_sonnet3.7-nothink', 'file_transpiler_analysis_fundraising_crm_tree_src.database.db_operations_3_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_7_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_8_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_9_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_10_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_11_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_12_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_13_sonnet3.7-nothink', 'file_transpiler_analysis_fundraising_crm_tree_src.database.db_operations_4_sonnet3.7-nothink', 'file_transpiler_analysis_fundraising_crm_tree_src.database.db_operations_5_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_14_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_15_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_16_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_17_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_18_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_19_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_20_sonnet3.7-nothink', 'file_transpiler_analysis_fundraising_crm_tree_src.database.db_operations_6_sonnet3.7-nothink', 'file_transpiler_analysis_fundraising_crm_tree_src.database.db_operations_7_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_21_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_22_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_23_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_24_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_25_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_26_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_27_sonnet3.7-nothink', 'file_transpiler_analysis_fundraising_crm_tree_src.database.db_operations_8_sonnet3.7-nothink', 'file_transpiler_analysis_fundraising_crm_tree_src.database.db_operations_9_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_28_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_29_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_30_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_31_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_32_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_33_sonnet3.7-nothink', 'file_transpiler_transpilation_fundraising_crm_tree_src.database.db_operations_34_sonnet3.7-nothink']


    test_file_name = "correctness_prompt.txt"

    pc.rate_corr_prompt(gen_entries, test_file_name)
