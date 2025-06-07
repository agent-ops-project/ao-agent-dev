# Parse a Python code base


## Static analysis

We use Pysa (from Pyre) for the static analysis. Some pitfalls:

 - Try to add `__init__.py__` to the porject repo (and parent): ƛ Invalid configuration: Cannot find any source files to analyze. Either `source_directories` or `targets` must be specified. 

 - Sometimes you need to: `export PYRE_VERSION=client_and_binary`

You can then do `pyre init` to set up a config.