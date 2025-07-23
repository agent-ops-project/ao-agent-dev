import os
from openai import OpenAI

from runtime_tracing.taint_wrappers import is_tainted, get_taint_origins

client = OpenAI()
engine = "gpt-4o"
q_string = "What's up?"
PDF_PATH = "/Users/ferdi/Downloads/ken_udbms_execution.pdf"

response = client.responses.create(
    model="gpt-3.5-turbo",
    input="Output the number 42 and nothing else"
)

print("After responses.create:")
print("  is_tainted(response):", is_tainted(response))
print("  is_tainted(response.output_text):", is_tainted(response.output_text))
print("  get_taint_origins(response.output_text):", get_taint_origins(response.output_text))

# q_string = response.output_text


with open(PDF_PATH, "rb") as f:
    assert os.path.isfile(PDF_PATH), f"File not found: {PDF_PATH}"
    file_response = client.files.create(
        file=(os.path.basename(PDF_PATH), f, "application/pdf"),
        purpose="assistants"
    )
    file_content = file_response.id

assistant = client.beta.assistants.create(
    name="Document Assistant",
    instructions=response.output_text,
    model=engine,
    tools=[{"type": "file_search"}],
)
# Create a thread and attach the file to the message
thread = client.beta.threads.create(
    messages=[{
        "role": "user", "content": q_string,
        # Attach the new file to the message.
        "attachments": [{ "file_id": file_content, "tools": [{"type": "file_search"}] }],
    }]
)

print("Before runs.create_and_poll:")
print("  is_tainted(q_string):", is_tainted(q_string))
print("  get_taint_origins(q_string):", get_taint_origins(q_string))
print("  is_tainted(thread):", is_tainted(thread))
print("  get_taint_origins(thread):", get_taint_origins(thread))
print("  is_tainted(assistant):", is_tainted(assistant))
print("  get_taint_origins(assistant):", get_taint_origins(assistant))

run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id, assistant_id=assistant.id
)

print("After runs.create_and_poll:")
print("  is_tainted(run):", is_tainted(run))
print("  get_taint_origins(run):", get_taint_origins(run))

messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
message_content = messages[0].content[0].text
annotations = message_content.annotations


