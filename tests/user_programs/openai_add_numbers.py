from openai import OpenAI


client = OpenAI()
model = "undefined_model"  # Make sure cache is used.

response = client.responses.create(
    model=model, input=f"Output the number 42 and nothing else", temperature=0
)

# Depends on OpenAI API version ...
# response = response.output_text
# prompt_add_1 = f"Add 1 to {response} and just output the result."
# prompt_add_2 = f"Add 2 to {response} and just output the result."
response_text = response.output[0].content[0].text
prompt_add_1 = f"Add 1 to {response_text} and just output the result."
prompt_add_2 = f"Add 2 to {response_text} and just output the result."

response1 = client.responses.create(model=model, input=prompt_add_1, temperature=0)
response2 = client.responses.create(model=model, input=prompt_add_2, temperature=0)

# Depends on OpenAI API version ...
# sum_prompt = f"Add these two numbers together and just output the result: {response1.output_text} + {response2.output_text}"
sum_prompt = f"Add these two numbers together and just output the result: {response1.output[0].content[0].text} + {response2.output[0].content[0].text}"

final_sum = client.responses.create(model=model, input=sum_prompt, temperature=0)
