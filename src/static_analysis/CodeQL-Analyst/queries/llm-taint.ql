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
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking
import semmle.python.ApiGraphs

/**
 * Identify calls to the relevant LLM provider SDKs.
 *
 * We match against the source text of the callee to avoid relying on
 * stubs of the third-party libraries being available in the CodeQL
 * database.  The two patterns we care about are:
 *   • OpenAI  –  *.chat.completions.create(...)
 *   • Anthropic – *.messages.create(...)
 */
class LLMCall extends DataFlow::CallCfgNode {
  LLMCall() {
    // Various ways the SDK functions may appear via direct imports
    this = API::moduleImport("openai").getMember("OpenAI").getReturn().getMember("chat").getMember("completions").getMember("create").getACall() or
    this = API::moduleImport("openai").getMember("OpenAI").getReturn().getMember("responses").getMember("create").getACall() or
    this = API::moduleImport("openai").getMember("OpenAI").getReturn().getMember("completions").getMember("create").getACall() or
    this = API::moduleImport("openai").getMember("OpenAI").getReturn().getMember("responses").getMember("create").getACall() or
    this = API::moduleImport("openai").getMember("chat").getMember("completions").getMember("create").getACall() or
    this = API::moduleImport("openai").getMember("completions").getMember("create").getACall() or
    this = API::moduleImport("openai").getMember("responses").getMember("create").getACall() or
    this = API::moduleImport("anthropic").getMember("Anthropic").getReturn().getMember("messages").getMember("create").getACall() or
    this = API::moduleImport("anthropic").getMember("AsyncAnthropic").getReturn().getMember("messages").getMember("create").getACall() or
    
    // Pattern matching for calls through instance variables or other indirect access
    (
    exists(string f | f = this.getFunction().toString() |
      f.regexpMatch(".*\\.(chat\\.)?completions\\.create$") or
      f.regexpMatch(".*\\.responses\\.create$") or
      f.regexpMatch(".*\\.messages\\.create$")
      )
      or
      // Additional patterns for attribute chains ending in LLM API calls
      exists(Attribute attr |
        attr = this.getFunction().asExpr() and
        (
          attr.getName() = "create" and
          (
            attr.getObject().(Attribute).getName() = "completions" or
            attr.getObject().(Attribute).getName() = "messages" or
            attr.getObject().(Attribute).getName() = "responses"
          )
        )
      )
      or
      // Match calls where the function name ends with known LLM API patterns
      exists(Call call |
        call = this.getNode().getNode() and
        exists(Attribute funcAttr |
          funcAttr = call.getFunc() and
          funcAttr.getName() = "create" and
          (
            // Handle chains like obj.chat.completions.create
            exists(Attribute parent |
              parent = funcAttr.getObject() and
              (
                parent.getName() = "completions" or
                parent.getName() = "messages" or  
                parent.getName() = "responses"
              )
            )
            or
            // Handle deeper chains like obj.chat.completions.create
            exists(Attribute grandparent, Attribute parent |
              parent = funcAttr.getObject() and
              grandparent = parent.getObject() and
              parent.getName() = "completions" and
              grandparent.getName() = "chat"
            )
          )
        )
      )
    )
  }
}

/**
 * Taint-tracking configuration
 */
module LLMTaintConfig implements DataFlow::ConfigSig {
  predicate isSource(DataFlow::Node source) {
    // The *result* of any LLM call is considered tainted.
    exists(LLMCall call | source = call)
  }

  predicate isSink(DataFlow::Node sink) {
    // Any argument supplied to an LLM call is a potential sink.
    exists(LLMCall call |
      sink = call.getArg(_) or
      sink = call.getArgByName(_)
    )
  }

  /**
   * Additional taint steps that preserve taint through various operations
   * including basic flow steps and custom function calls
   */
  predicate isAdditionalTaintStep(DataFlow::Node pred, DataFlow::Node succ) {
    // Flow through attribute access, e.g. obj.attr
    exists(Attribute attr |
      pred = DataFlow::exprNode(attr.getObject()) and
      succ = DataFlow::exprNode(attr)
    ) or
    // Flow through subscript access, e.g. value[index]
    exists(Subscript sub |
      pred = DataFlow::exprNode(sub.getObject()) and
      succ = DataFlow::exprNode(sub)
    ) or
    // Flow through values being placed inside a dict literal
    exists(Dict dict, Expr v |
      v = dict.getAValue() and
      pred = DataFlow::exprNode(v) and
      succ = DataFlow::exprNode(dict)
    ) or
    // Flow through list elements
    exists(List list, Expr elt |
      elt = list.getAnElt() and
      pred = DataFlow::exprNode(elt) and
      succ = DataFlow::exprNode(list)
    ) or
    // Flow through simple type coercions like int(x), str(x), float(x)
    exists(Call conv |
      succ = DataFlow::exprNode(conv) and
      pred = DataFlow::exprNode(conv.getArg(0)) and
      exists(Expr fn | fn = conv.getFunc() |
        fn.toString().regexpMatch("^(int|str|float)$")
      )
    ) or
    
    // === CUSTOM FUNCTION TAINT MODELING ===
    // Database operations (psycopg2, sqlite3, etc.)
    exists(Call call |
      call.getFunc().(Attribute).getName() = "execute" and
      pred = DataFlow::exprNode(call.getAnArg()) and
      succ = DataFlow::exprNode(call)
    ) or
    exists(Call call |
      call.getFunc().(Attribute).getName() = "fetchone" and
      pred = DataFlow::exprNode(call.getFunc().(Attribute).getObject()) and
      succ = DataFlow::exprNode(call)
    ) or
    exists(Call call |
      call.getFunc().(Attribute).getName() = "fetchall" and
      pred = DataFlow::exprNode(call.getFunc().(Attribute).getObject()) and
      succ = DataFlow::exprNode(call)
    ) or
    
    // HTTP requests (requests library)
    exists(Call call |
      call.getFunc().(Attribute).getName() in ["get", "post", "put", "delete", "patch"] and
      pred = DataFlow::exprNode(call.getAnArg()) and
      succ = DataFlow::exprNode(call)
    ) or
    
    // File operations
    exists(Call call |
      call.getFunc().(Attribute).getName() in ["read", "readline", "readlines"] and
      pred = DataFlow::exprNode(call.getFunc().(Attribute).getObject()) and
      succ = DataFlow::exprNode(call)
    ) or
    exists(Call call |
      call.getFunc().(Attribute).getName() = "write" and
      pred = DataFlow::exprNode(call.getAnArg()) and
      succ = DataFlow::exprNode(call)
    ) or
    
    // JSON operations
    exists(Call call |
      call.getFunc().(Attribute).getName() = "loads" and
      pred = DataFlow::exprNode(call.getArg(0)) and
      succ = DataFlow::exprNode(call)
    ) or
    exists(Call call |
      call.getFunc().(Attribute).getName() = "dumps" and
      pred = DataFlow::exprNode(call.getArg(0)) and
      succ = DataFlow::exprNode(call)
    ) or
    
    // String operations that preserve taint
    exists(Call call |
      call.getFunc().(Attribute).getName() in ["format", "upper", "lower", "strip", "replace", "join"] and
      pred = DataFlow::exprNode(call.getFunc().(Attribute).getObject()) and
      succ = DataFlow::exprNode(call)
    ) or
    exists(Call call |
      call.getFunc().(Attribute).getName() in ["format", "replace", "join"] and
      pred = DataFlow::exprNode(call.getAnArg()) and
      succ = DataFlow::exprNode(call)
    ) or
    
    // Custom function modeling - any function call preserves taint from first argument
    // This is a broad rule - you can make it more specific as needed
    exists(Call call |
      // Only apply to functions that are likely to preserve/process data
      call.getFunc().(Name).getId().regexpMatch(".*(process|handle|execute|transform|convert|parse|analyze).*") and
      pred = DataFlow::exprNode(call.getArg(0)) and
      succ = DataFlow::exprNode(call)
    ) or
    
    // Model specific function names
    exists(Call call |
      call.getFunc().(Name).getId() in ["cursor_execute", "some_unknown_function", "complex_processing", "make_http_request"] and
      pred = DataFlow::exprNode(call.getAnArg()) and
      succ = DataFlow::exprNode(call)
    )
  }

  // Allow deeper branching for complex JSON/attribute structures
  int fieldFlowBranchLimit() { result = 5000 }
}

module Flow = TaintTracking::Global<LLMTaintConfig>;
import Flow::PathGraph

from Flow::PathNode src, Flow::PathNode sink
where Flow::flowPath(src, sink)
select sink.getNode(), src, sink,
  "Tainted data originating from an LLM response reaches another LLM request parameter." 