from openai import OpenAI

def main():
    client = OpenAI()

    response = client.responses.create(
        model="gpt-3.5-turbo", input=f"Output the number 42 and nothing else", temperature=0
    )

    print(response)

    response = response.output_text

    print("response 0", response)

    prompt_add_1 = f"Add 1 to {response} and just output the result."
    prompt_add_2 = f"Add 2 to {response} and just output the result."

    print("response 1", prompt_add_1)
    print("response 2", prompt_add_2)

    response1 = client.responses.create(model="gpt-3.5-turbo", input=prompt_add_1, temperature=0)

    response2 = client.responses.create(model="gpt-3.5-turbo", input=prompt_add_2, temperature=0)

    sum_prompt = f"Add these two numbers together and just output the result: {response1.output_text} + {response2.output_text}"

    print("sum prompt", sum_prompt)

    final_sum = client.responses.create(model="gpt-3.5-turbo", input=sum_prompt, temperature=0)
    # print(f"Final sum: {final_sum}")


if __name__ == "__main__":
    main()
