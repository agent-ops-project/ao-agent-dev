/**
 * @name LLM API Taint Analysis
 * @description Detects data flows from one LLM API call to another LLM API call
 * @kind path-problem
 * @precision high
 * @id python/llm-taint-flow
 * @tags security
 * @problem.severity warning
 */

import python
import semmle.python.dataflow.new.DataFlow         // for exprNode()
import semmle.python.dataflow.new.TaintTracking

/**
 * Matches any Python call expression whose function text
 * ends in chat.completions.create, responses.create, or messages.create.
 */
class LLMCall extends Call {
  LLMCall() {
    this.getFunc().toString().regexpMatch(".*\\.(chat\\.)?completions\\.create$") or
    this.getFunc().toString().regexpMatch(".*\\.responses\\.create$")        or
    this.getFunc().toString().regexpMatch(".*\\.messages\\.create$")
  }
}

module LLMTaintConfig implements DataFlow::ConfigSig {
  /** The *result* of an LLM call (the Call node itself) is tainted */
  predicate isSource(DataFlow::Node source) {
    exists(LLMCall call |
      source = DataFlow::exprNode(call)
    )
  }

  /** Any argument expression passed into an LLM call is a sink */
  predicate isSink(DataFlow::Node sink) {
    exists(LLMCall call |
      // positional args
      exists(Expr arg |
        arg in call.getPositionalArgs() and
        sink = DataFlow::exprNode(arg)
      ) or
      // named args
      exists(Expr arg |
        arg in call.getNamedArgs() and
        sink = DataFlow::exprNode(arg)
      )
    )
  }

  /**
   * Non-value-preserving propagation (attributes, indexing,
   * collection literals, and simple coercions)
   */
  predicate isAdditionalFlowStep(DataFlow::Node pred, DataFlow::Node succ) {
    exists(Attribute attr |
      pred = DataFlow::exprNode(attr.getObject()) and
      succ = DataFlow::exprNode(attr)
    ) or
    exists(Subscript sub |
      pred = DataFlow::exprNode(sub.getObject()) and
      succ = DataFlow::exprNode(sub)
    ) or
    exists(Dict dict, Expr v |
      v    = dict.getAValue() and
      pred = DataFlow::exprNode(v)      and
      succ = DataFlow::exprNode(dict)
    ) or
    exists(List list, Expr elt |
      elt  = list.getAnElt() and
      pred = DataFlow::exprNode(elt)   and
      succ = DataFlow::exprNode(list)
    ) or
    exists(Call conv |
      succ = DataFlow::exprNode(conv) and
      pred = DataFlow::exprNode(conv.getAPositionalArg(0)) and
      exists(Expr fn | fn = conv.getFunc() |
        fn.toString().regexpMatch("^(int|str|float)$")
      )
    )
  }

  // allow deeper branching on JSON/attr structures
  int fieldFlowBranchLimit() { result = 5000 }
}

module Flow = TaintTracking::Global<LLMTaintConfig>;
import Flow::PathGraph

from Flow::PathNode src, Flow::PathNode sink
where Flow::flowPath(src, sink)
select
  sink.getNode(), src, sink,
  "Tainted data originating from an LLM response reaches another LLM request parameter."
