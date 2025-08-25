GET_INPUT = """Below is the full input dict to an LLM API call:

{input_dict}

You need to write function `{function_name}` that extracts the LLM input string (i.e., disregarding further parameters such as model choice).

Below is an example of such a function:

```
def _get_input_openai_responses_create(input_obj: any) -> str:
    return response.output[0].content[0].text
```

Now, write `{function_name}`. Format your response as follows:

<identify_input>
Describe what the input in the given dict is and how it can be extracted.
</identify_input>

<implementation>
Provide the full implementation of `{function_name}`. Don't provide anything else except Python code.
</implementation>
"""

SET_INPUT = """
You're given the kwargs dict that will be passed to an LLM API call. You need to write a function that overwrites the input inside the dict, such that the LLM is called with a different prompt. This involves the following steps:

1. Load the input dict using dill.
2. Overwrite the input inside the dict.
3. Convert the dict back to a pickle using dill.

Here is an example of such a function that implements the above logic for a specific API call:

```
def _set_input_openai_responses_create(prev_input_pickle: bytes, new_input_text: str) -> bytes:
    input_obj = dill.loads(prev_input_pickle)
    input_obj["input"] = new_input_text
    return dill.dumps(input_obj)
```

Now implement `{function_name}` to handle dicts like the following:

{input_dict}

Format your response as follows:

<explanation>
Outline what the input in the input dict is and how you can overwrite it.
</explanation>

<implementation>
Provide the full implementation of `{function_name}`. Don't provide anything else except Python code.
</implementation>
"""

GET_OUTPUT = """Below is the output object returned by an LLM API call:

{output_obj}

You need to write function `{function_name}` that extracts the LLM output string (i.e., disregarding further parameters such as logprobs).

Below is an example of such a function:

```
def _get_output_openai_responses_create(response_obj: bytes) -> str:
    return response_obj.output[-1].content[-1].text
```

Now, write `{function_name}`. Format your response as follows:

<identify_output>
Describe what the output in the given object is and how it can be extracted.
</identify_output>

<implementation>
Provide the full implementation of `{function_name}`. Don't provide anything else except Python code.
</implementation>
"""

SET_OUTPUT = """Below is the output object returned by an LLM API call:

{output_obj}

1. Load the input dict using dill.
2. Overwrite the input inside the dict.
3. Convert the dict back to a pickle using dill.

You need to write function `{function_name}` that extracts the LLM output string (i.e., disregarding further parameters such as logprobs).

Here is an example of such a function that implements the above logic for a specific API call:

```
def _set_output_openai_responses_create(prev_output_pickle: bytes, output_text: str) -> bytes:
    response_obj = dill.loads(prev_output_pickle)
    response_obj.output[-1].content[-1].text = output_text
    return dill.dumps(response_obj)
```

Now implement `{function_name}`. Format your response as follows:

<explanation>
Outline what the output in the `response_obj` is and how you can overwrite it.
</explanation>

<implementation>
Provide the full implementation of `{function_name}`. Don't provide anything else except Python code.
</implementation>
"""


INSTALL_SET_AND_GET = """
Carefully read @src/workflow_edits/utils.py. It contains functions that allow to read and overwrite the inputs dictionaries (kwargs) and output response objects of LLM API calls. Your job is to add support for another API type: {api_type}

You're given the following four functions that handle this new API type:

{get_input}

{set_input}

{get_output}

{set_output}

Add them to the src/workflow_edits/utils.py file and include them in the case switches of `get_input`, `set_input_string`, `get_output_string` and `set_output_string` function respectively."""


WRITE_PATCH = """
TODO
"""

INSTALL_PATCH = """
TODO
"""

ADD_TO_TEST = """
TODO
"""
