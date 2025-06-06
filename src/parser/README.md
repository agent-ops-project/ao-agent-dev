# Parse a Python code base


## Static analysis

We use Pysa (from Pyre) for the static analysis.

Pyre has some weird thing where you need to do:

`export PYRE_VERSION=client_and_binary`

You can then do `pyre init` to set up a config.