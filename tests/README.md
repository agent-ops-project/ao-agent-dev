# Tests

## How we run tests

We run a test inside an `aco-launch` process, the same way that the user would run the test program in practice. However, `aco-launch` has overheads which makes running 100s of tests slow. To overcome this, we run all tests in a file (e.g., `test_re_patches.py`) inside the same `aco-launch` process as if they were one program sequentially executing each test. For all tests, we individually record if they failed and the Traceback of failing tests. We then send this information back to pytest, which launched the `aco-launch` process and logs test failures on a per-test granularity.

Our tool rewrites the test ASTs for taint tracking, the same way this would be done with the user's code base. To support this, we set the repository_root to the directory of the tests that need to be rewritten (i.e., `aco-launch --project-root`). 

## Adding tests

## Debugging heads up

For `test_api_calls.py`, the user progam is executed as a replay by the server. So you need to run `aco-server logs` to see the output of the user program (e.g., how it crashed).