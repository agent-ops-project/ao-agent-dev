from runtime_tracing.generate_patch_prompts import *
from openai import OpenAI
from html.parser import HTMLParser
from claude_code_sdk import query, ClaudeSDKClient, ClaudeCodeOptions

from runtime_tracing.generate_patch_prompts import INSTALL_SET_AND_GET


# 1. Get get_input function.
def _1_get_input(input_dict, function_id):
    function_signature = f"def _get_input_{function_id}(input_dict: any) -> str:"
    prompt = GET_INPUT.format(input_dict=input_dict, function_name=function_signature)
    return _call_openai(prompt)


# 2. Get set_input function.
def _2_set_input(input_dict, function_id):
    function_signature = (
        f"def _set_input_{function_id}(prev_input_pickle: bytes, new_input_text: str) -> bytes:"
    )
    prompt = SET_INPUT.format(input_dict=input_dict, function_name=function_signature)
    return _call_openai(prompt)


# 3. Get get_output function.
def _3_get_output(output_obj, function_id):
    function_signature = f"def _get_output_{function_id}(response_obj: bytes) -> str:"
    prompt = GET_OUTPUT.format(output_obj=output_obj, function_name=function_signature)
    return _call_openai(prompt)


# 4. Get set_output function.
def _4_set_output(output_obj, function_id):
    function_signature = (
        f"def _set_output_{function_id}(prev_input_pickle: bytes, new_output_text: str) -> bytes:"
    )
    prompt = SET_OUTPUT.format(output_obj=output_obj, function_name=function_signature)
    return _call_openai(prompt)


# 5. Install set and get.
async def _5_install_set_and_get(api_type, get_input, set_input, get_output, set_output):
    # prompt = INSTALL_SET_AND_GET.format(api_type=api_type, get_input=get_input, set_input=set_input, get_output=get_output, set_output=set_output)

    prompt = """Carefully read @src/workflow_edits/utils.py. It contains functions that allow to read and overwrite the inputs dictionaries (kwargs) and output response objects of LLM API calls. Your job is to add support for another API type: together.resources.chat.completions.ChatCompletions.create

You're given the following four functions that handle this new API type:

unavailable

```python
import dill

def _set_input_together_resources_chat_completions_ChatCompletions_create(prev_input_pickle: bytes, new_input_text: str) -> bytes:
    input_obj = dill.loads(prev_input_pickle)
    input_obj['messages'][0]['content'] = new_input_text
    return dill.dumps(input_obj)
```

```python
def _get_output_together_resources_chat_completions_ChatCompletions_create(response_obj: bytes) -> str:
    import json
    response = json.loads(response_obj)
    return response['choices'][0]['message']['content']
```

```python
import dill

def _set_output_together_resources_chat_completions_ChatCompletions_create(prev_input_pickle: bytes, new_output_text: str) -> bytes:
    response_obj = dill.loads(prev_input_pickle)
    response_obj.choices[0].message.content = new_output_text
    return dill.dumps(response_obj)
```

Add them to the src/workflow_edits/utils.py file and include them in the case switches of `get_input`, `set_input_string`, `get_output_string` and `set_output_string` function respectively.
"""

    options = ClaudeCodeOptions(
        permission_mode="acceptEdits",
        allowed_tools=["Read", "Write", "Bash", "Replace", "Edit", "FileWrite", "FileEdit"],
    )

    # Use the query function directly, not ClaudeSDKClient
    async for message in query(prompt=prompt, options=options):
        print(f"Message type: {type(message)}")
        print(f"Message: {message}")

        # Check for different message types
        if hasattr(message, "content"):
            print(f"Content: {message.content}")


# =================================================
# Call LLM helpers.
# =================================================
client = OpenAI()


def _call_openai(input, model="gpt-4o"):
    response = client.responses.create(model=model, input=input, temperature=0)
    return response.output[0].content[0].text


# =================================================
# Parse LLM response.
# =================================================
class TagContentExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = {}
        self.current_tag = None
        self.current_data = []

    def handle_starttag(self, tag, attrs):
        """Called when an opening tag is encountered"""
        self.current_tag = tag
        self.current_data = []  # Reset data collection for new tag

    def handle_endtag(self, tag):
        """Called when a closing tag is encountered"""
        if self.current_tag == tag and self.current_data:
            # Join all data pieces and strip whitespace
            content = "".join(self.current_data).strip()
            if content:  # Only add non-empty content
                self.result[tag] = content
        self.current_tag = None
        self.current_data = []

    def handle_data(self, data):
        """Called when text data is encountered"""
        if self.current_tag:
            self.current_data.append(data)

    def get_result(self):
        """Return the extracted dictionary"""
        return self.result


def extract_tag_content(html_string):
    """
    Extract content from HTML-like tags into a dictionary.
    """
    parser = TagContentExtractor()
    parser.feed(html_string)
    return parser.get_result()
