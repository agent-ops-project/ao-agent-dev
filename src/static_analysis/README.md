# Static analysis

Static analysis to compute data flow between LLM calls. This doesn't fully work yet on very complex code bases, so it is messy. On simpler code bases it works fine.

I tried two frameworks:

## Pyre

From Meta. Supports incremental update, so it is faster. This is my preferred framework. `pyre_analysis` is the one to look at, I'm keeping the other dir around just for reference.

## CodeQL

From github, idea is to have a query language over code. Learning the language is kind of complicated but once you get it, it's kind of cool. A big problem is that there are no incremental updates like for Pyre, so it takes long to perform the analysis on big code bases.
