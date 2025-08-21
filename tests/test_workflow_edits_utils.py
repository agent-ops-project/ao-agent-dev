import pytest
import dill
from unittest.mock import Mock, MagicMock
from types import SimpleNamespace

from workflow_edits.utils import (
    get_input_string,
    set_input_string,
    get_output_string,
    set_output_string,
    get_model_name,
)


class TestWorkflowEditsUtils:
    """Test input/output manipulation functions for all supported API types."""

    def test_openai_chat_completions_create(self):
        """Test OpenAI chat completions API type."""
        api_type = "OpenAI.chat.completions.create"

        # Test input
        input_obj = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello world"},
            ],
        }

        # Test get_input
        input_text, attachments = get_input_string(input_obj, api_type)
        assert input_text == "Hello world"
        assert attachments == []

        # Test set_input and get_input again
        input_pickle = dill.dumps(input_obj)
        new_input_text = "Modified input"
        modified_pickle = set_input_string(input_pickle, new_input_text, api_type)
        modified_obj = dill.loads(modified_pickle)

        modified_input_text, _ = get_input_string(modified_obj, api_type)
        assert modified_input_text == new_input_text

        # Test output
        response_obj = Mock()
        response_obj.choices = [Mock()]
        response_obj.choices[0].message = Mock()
        response_obj.choices[0].message.content = "Original response"

        # Test get_output
        output_text = get_output_string(response_obj, api_type)
        assert output_text == "Original response"

        # Test set_output and get_output again
        response_pickle = dill.dumps(response_obj)
        new_output_text = "Modified response"
        modified_response_pickle = set_output_string(response_pickle, new_output_text, api_type)
        modified_response_obj = dill.loads(modified_response_pickle)

        modified_output_text = get_output_string(modified_response_obj, api_type)
        assert modified_output_text == new_output_text

        # Test get_model
        model_name = get_model_name(input_obj, api_type)
        assert model_name == "gpt-3.5-turbo"

    def test_async_openai_chat_completions_create(self):
        """Test AsyncOpenAI chat completions API type."""
        api_type = "AsyncOpenAI.chat.completions.create"

        input_obj = {"model": "gpt-4", "messages": [{"role": "user", "content": "Test async"}]}

        input_text, _ = get_input_string(input_obj, api_type)
        assert input_text == "Test async"

        input_pickle = dill.dumps(input_obj)
        new_text = "New async input"
        modified_pickle = set_input_string(input_pickle, new_text, api_type)
        modified_obj = dill.loads(modified_pickle)

        modified_input_text, _ = get_input_string(modified_obj, api_type)
        assert modified_input_text == new_text

    def test_openai_responses_create(self):
        """Test OpenAI responses API type."""
        api_type = "OpenAI.responses.create"

        input_obj = {"input": "Test input", "model": "text-davinci-003"}

        # Test get_input - note: returns tuple but function signature suggests string
        input_text, attachments = get_input_string(input_obj, api_type)
        assert input_text == "Test input"
        assert attachments is None

        # Test set_input
        input_pickle = dill.dumps(input_obj)
        new_input_text = "Modified input"
        modified_pickle = set_input_string(input_pickle, new_input_text, api_type)
        modified_obj = dill.loads(modified_pickle)
        assert modified_obj["input"] == new_input_text

    def test_anthropic_messages_create(self):
        """Test Anthropic messages API type."""
        api_type = "Anthropic.messages.create"

        # Test simple string content
        input_obj = {
            "model": "claude-3-sonnet-20240229",
            "messages": [{"role": "user", "content": "Hello Claude"}],
        }

        input_text, attachments = get_input_string(input_obj, api_type)
        assert input_text == "Hello Claude"
        assert attachments == []

        # Test multimodal content
        input_obj_multimodal = {
            "model": "claude-3-sonnet-20240229",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this document"},
                        {"type": "document", "source": {"type": "base64", "data": "..."}},
                    ],
                }
            ],
        }

        input_text, attachments = get_input_string(input_obj_multimodal, api_type)
        assert input_text == "Analyze this document"
        assert len(attachments) == 1
        assert attachments[0] == ("document.pdf", "base64_embedded")

        # Test set_input
        input_pickle = dill.dumps(input_obj)
        new_input_text = "Modified Anthropic input"
        modified_pickle = set_input_string(input_pickle, new_input_text, api_type)
        modified_obj = dill.loads(modified_pickle)

        modified_input_text, _ = get_input_string(modified_obj, api_type)
        assert modified_input_text == new_input_text

        # Test output
        response_obj = Mock()
        response_obj.content = [Mock()]
        response_obj.content[0].text = "Anthropic response"

        output_text = get_output_string(response_obj, api_type)
        assert output_text == "Anthropic response"

        # Test set_output
        response_pickle = dill.dumps(response_obj)
        new_output_text = "Modified Anthropic response"
        modified_response_pickle = set_output_string(response_pickle, new_output_text, api_type)
        modified_response_obj = dill.loads(modified_response_pickle)

        modified_output_text = get_output_string(modified_response_obj, api_type)
        assert modified_output_text == new_output_text

    def test_vertexai_client_models_generate_content(self):
        """Test VertexAI generate content API type."""
        api_type = "vertexai client_models_generate_content"

        input_obj = {"contents": "Test VertexAI input", "model": "gemini-pro"}

        input_text, attachments = get_input_string(input_obj, api_type)
        assert input_text == "Test VertexAI input"
        assert attachments is None

        # Test set_input
        input_pickle = dill.dumps(input_obj)
        new_input_text = "Modified VertexAI input"
        modified_pickle = set_input_string(input_pickle, new_input_text, api_type)
        modified_obj = dill.loads(modified_pickle)
        assert modified_obj["contents"] == new_input_text

        # Test output - mock VertexAI response structure
        response_obj = Mock()
        response_obj.text = "VertexAI response"
        response_obj.model_dump.return_value = {
            "candidates": [{"content": {"parts": [{"text": "VertexAI response"}]}}]
        }

        output_text = get_output_string(response_obj, api_type)
        assert output_text == "VertexAI response"

    def test_openai_beta_threads_create(self):
        """Test OpenAI beta threads API type."""
        api_type = "OpenAI.beta.threads.create"

        # Mock input object structure
        input_obj = Mock()
        input_obj.content = [Mock()]
        input_obj.content[0].text = Mock()
        input_obj.content[0].text.value = "Thread input"
        input_obj.attachments = []
        input_obj.model = "gpt-4"

        input_text, attachments = get_input_string(input_obj, api_type)
        assert input_text == "Thread input"
        assert attachments == []

        # Test output
        response_obj = Mock()
        response_obj.content = [Mock()]
        response_obj.content[0].text = Mock()
        response_obj.content[0].text.value = "Thread response"

        output_text = get_output_string(response_obj, api_type)
        assert output_text == "Thread response"

    def test_together_chat_completions_create(self):
        """Test Together chat completions API type."""
        api_type = "together.resources.chat.completions.ChatCompletions.create"

        input_obj = {
            "model": "openai/gpt-oss-120b",
            "messages": [{"role": "user", "content": "Together input"}],
        }

        input_text, attachments = get_input_string(input_obj, api_type)
        assert input_text == "Together input"
        assert attachments == []

        # Test set_input
        input_pickle = dill.dumps(input_obj)
        new_input_text = "Modified Together input"
        modified_pickle = set_input_string(input_pickle, new_input_text, api_type)
        modified_obj = dill.loads(modified_pickle)

        modified_input_text, _ = get_input_string(modified_obj, api_type)
        assert modified_input_text == new_input_text

        # Test output - Together returns JSON string
        response_json = b'{"choices": [{"message": {"content": "Together response"}}]}'

        output_text = get_output_string(response_json, api_type)
        assert output_text == "Together response"

    def test_unknown_api_type(self):
        """Test that unknown API types raise ValueError."""
        unknown_api_type = "unknown.api.type"

        with pytest.raises(ValueError, match="Unknown API type"):
            get_input_string({}, unknown_api_type)

        with pytest.raises(ValueError, match="Unknown API type"):
            set_input_string(b"", "test", unknown_api_type)

        with pytest.raises(ValueError, match="Unknown API type"):
            get_output_string(b"", unknown_api_type)

        with pytest.raises(ValueError, match="Unknown API type"):
            set_output_string(b"", "test", unknown_api_type)

        with pytest.raises(ValueError, match="Unknown API type"):
            get_model_name({}, unknown_api_type)

    def test_roundtrip_all_api_types(self):
        """Test complete roundtrip for all API types."""
        test_cases = [
            (
                "OpenAI.chat.completions.create",
                {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "test"}]},
            ),
            (
                "AsyncOpenAI.chat.completions.create",
                {"model": "gpt-4", "messages": [{"role": "user", "content": "async test"}]},
            ),
            (
                "Anthropic.messages.create",
                {
                    "model": "claude-3-sonnet-20240229",
                    "messages": [{"role": "user", "content": "anthropic test"}],
                },
            ),
            (
                "vertexai client_models_generate_content",
                {"contents": "vertex test", "model": "gemini-pro"},
            ),
            (
                "together.resources.chat.completions.ChatCompletions.create",
                {
                    "model": "openai/gpt-oss-120b",
                    "messages": [{"role": "user", "content": "together test"}],
                },
            ),
        ]

        for api_type, input_obj in test_cases:
            # Test input roundtrip
            original_input = get_input_string(input_obj, api_type)[0]

            input_pickle = dill.dumps(input_obj)
            new_input = "modified test input"
            modified_pickle = set_input_string(input_pickle, new_input, api_type)
            modified_obj = dill.loads(modified_pickle)

            retrieved_input = get_input_string(modified_obj, api_type)[0]
            assert retrieved_input == new_input, f"Input roundtrip failed for {api_type}"
