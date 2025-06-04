instructions = """I'm translating code from a high-level description into runnable Python code using LLMs. I take several steps to do this, and my final code is wrong. I want to figure out which was the first step that was to unclear or incorrect, such that the later steps couldn't recover from that failure. Erros could include describing a wrong design, being to inconcise, or simply not producing the right code although the previously described approach is perfectly clear. Be critical in your analysis of every step and consider each step as a possible root cause for the final error (i.e., even steps that don't produce code may be inconcise and therefore result in the wrong code). The code is part of a larger code base. The high-level task description describes functionality and what dependencies to use (e.g., dependencies inside the repo and extermal packages).

1. First, I'm doing an analysis of the high-level text. This produces a difficulty rating and description of what the LLM struggled with.
2. Second, I'm planning the implementation in several iterations. This produces high-level code that becomes more and more concrete.
3. I'm generating the actual source code. I will give you the code here and a review that the LLM gets on the generated code.

Below are all the steps and the LLM's output for the step:

---------------------------------------------
Step 1: Analyzing the high-level task description:

{analysis}"""

# TODO: What is the below?? Probably don't need it?
"""
---------------------------------------------
Step {iter}: Iteratively planning the implementation:

{plan}
---------------------------------------------
Step {iter}: Implementing the actual code (implementation and review):

Implemmentation:
{implementation}

Review:
{review}
---------------------------------------------
"""



plan_prompt = """
---------------------------------------------
Step {iter}: Iteratively planning the implementation:

Produced plan (iteratively refined Python code):

{plan}

Performed steps:

{analysis}
"""


rate_correctness_prompt = """
I have a high-level design doc and want to turn it into code using LLMs. I chain together several LLM calls to achieve this, were I first have a planning phase and then a transpilation phase.

Below are an outputs and review for one of the steps. Based on the output and the review, I want you to label the step's correctness as either 'certainly correct', 'uncertain', or 'certainly wrong'.

Your rating must only contain one of these three values. This is how you should assign them:

1. 'certainly correct': Based on code and review, the step produced an output that is certainly correct and will not cause any problems further down the transpilation process.

2. 'uncertain': It is hard to tell whether the output is correct or incorrect.

3. 'certainly incorrect': Based on code and review, the step produced an output that is certainly incorrect as is. The problems might be fixable in the future but the current output is erreneous, either by being too vague, underspecified or producing wrong code (e.g., code that doesn't compile).

Here is the LLM's output:
---------------------------------------------
{output}
---------------------------------------------

Here is the review to this output:
---------------------------------------------
{review}
---------------------------------------------

Give an overall rating of the output that also considers the review. The review must be one of the following three values: 'certainly correct', 'uncertain', or 'certainly wrong'

Wrap your answer into a <rating> tag, i.e.:

<rating>
'certainly correct', 'uncertain', or 'certainly wrong'
</rating>
"""


impl_prompt = """
---------------------------------------------
Step {iter}: Implementing the actual code (implementation and review):

Implemmentation:

{implementation}

Review:

{review}
"""

suffix = """
In your response, describe what step is the root cause of the wrong code generation (i.e., after which step what the LLM chain not able to recover --- e.g, because it's too vaguely or badly planned, or the LLM generated incorrect code although the task was perfectly clear). First, reason about what went wrong in the generation process. Then, describe where it went wrong first. Then describe what is necessary to avoid this failure.
"""


test_prompt = """
The failing test case is `test_task_management_workflow` in `test_agent_service.py`. The error message is `TypeError: Task.__init__() got an unexpected keyword argument 'create_time'`. 

The error happens here in `test_agent_service.py`:

class IntegrationTestAgentService(unittest.TestCase):

    def setUp(self):
        # Create mock schema and database
        self.mock_schema = mock.Mock(spec=Schema)
        self.mock_database = mock.Mock(spec=PostgresOperations)
        
        # Create the agent service
        self.agent_service = AgentService(self.mock_schema, self.mock_database)
        
        # Create a mock agent for testing
        self.test_agent = Agent(
            agent_id=1,
            name="Test Agent",
            email="test@example.com",
            password="password123"
        )
        
        # Setup common test data
        self.test_company = Company(
            company_id=101,
            name="Test Company",
            main_contact_id=201,
            target_funding=100000,
            grant_type="Research",
            status="New",
            renewal_date="2023-12-31"
        )
        
        self.test_contact = Contact(
            contact_id=201,
            name="Test Contact",
            email="contact@example.com",
            company_id=101,
            assigned_agent_id=1,
            status="new"
        )
        
        self.test_task = Task(
            task_id=301,
            assigned_agent_id=1,
            contact_id=201,
            company_id=101,
            name="Test Task",
            description="Test Description",
            create_time="2023-01-01",
            due_time="2023-02-01",
            status="incomplete"
        )

In your response, describe what step is the root cause of the wrong code generation (i.e., after which step what the LLM chain not able to recover --- e.g, because it's too vaguely or badly planned, or the LLM generated incorrect code although the task was perfectly clear). First, reason about what went wrong in the generation process. Then, describe where it went wrong first. Then describe what is necessary to avoid this failure.

"""

