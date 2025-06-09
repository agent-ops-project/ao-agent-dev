# Runtime tracing

See which functions are executed at runtime.

`sitecustomize.py` applies the monkey patching. It intercepts all calls to LLMs and sends to the develop_server: Their input, output, file and line number, and the thread / asynio thread the LLM were called from.