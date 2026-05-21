"""Universal language-agnostic patterns."""

from __future__ import annotations

from collections import Counter

from adapters.contracts import SolvixFunction, SolvixNode
from core.report import PatternMatch


def run_universal_patterns(function: SolvixFunction) -> list[PatternMatch]:
    patterns: list[PatternMatch] = []
    nodes = function.nodes
    recursion_recorded = False

    for node in nodes:
        if node.node_type == "loop" and any(child.node_type in {"loop", "nested_loop"} for child in node.children):
            patterns.append(
                PatternMatch(
                    name="nested_loop",
                    severity="HIGH",
                    line=node.line_number,
                    explanation="Nested loop detected. Complexity is at minimum O(n²). Every full pass of the inner loop runs for each single iteration of the outer loop.",
                    suggestion="Consider flattening this logic, using hash maps for lookups instead of inner loops, or applying vectorized operations for numerical data.",
                )
            )
        if node.node_type == "memory_alloc" and _parent_is_loop(node, nodes):
            patterns.append(
                PatternMatch(
                    name="memory_allocation_in_loop",
                    severity="MEDIUM",
                    line=node.line_number,
                    explanation="Memory is being allocated on every iteration of this loop. Each allocation asks the system to find and reserve new space. This cost multiplies with every loop cycle.",
                    suggestion="Move the allocation outside the loop. Preallocate the full structure before the loop begins and fill it inside.",
                )
            )
        if node.depth >= 4:
            patterns.append(
                PatternMatch(
                    name="deep_nesting",
                    severity="LOW",
                    line=node.line_number,
                    explanation=f"This code is nested {node.depth} levels deep. Deep nesting hides performance problems and makes optimization harder.",
                    suggestion="Extract inner logic into separate named functions. Flat code is faster to read and easier to optimize.",
                )
            )
        if node.node_type == "recursion" and not recursion_recorded:
            recursion_recorded = True
            patterns.append(
                PatternMatch(
                    name="recursion_without_memoization",
                    severity="MEDIUM",
                    line=node.line_number,
                    explanation="This function calls itself recursively. Without memoization, the same inputs may be computed multiple times, growing the call stack unnecessarily.",
                    suggestion="Add memoization using a cache dictionary or your language's built-in decorator. Store results of previous calls and return them directly on repeat inputs.",
                )
            )
        if node.node_type == "string_concat" and _parent_is_loop(node, nodes):
            severity = "HIGH" if function.language == "java" else "MEDIUM"
            patterns.append(
                PatternMatch(
                    name="string_concatenation_in_loop",
                    severity=severity,
                    line=node.line_number,
                    explanation="String concatenation inside a loop creates a new string object on every iteration. Strings are immutable in most languages - this means new memory every cycle.",
                    suggestion="Use a string builder or join pattern. Collect parts in a list and join once outside the loop.",
                )
            )
        if node.node_type == "async_block" and _parent_is_loop(node, nodes):
            patterns.append(
                PatternMatch(
                    name="async_blocking_in_loop",
                    severity="CRITICAL",
                    line=node.line_number,
                    explanation="An async or concurrent operation is being created inside a loop. This either blocks the event loop on every iteration or spawns uncontrolled goroutines or threads.",
                    suggestion="Collect all async work first, then execute concurrently outside the loop using Promise.all, asyncio.gather, or equivalent for your language.",
                )
            )
        if node.node_type == "data_copy" and _parent_is_loop(node, nodes):
            patterns.append(
                PatternMatch(
                    name="data_copy_in_loop",
                    severity="MEDIUM",
                    line=node.line_number,
                    explanation="Data is being copied on every loop iteration. Copying creates new memory allocations and increases the work the garbage collector must do.",
                    suggestion="Pass references or pointers where possible. Only copy when mutation is required.",
                )
            )
        if node.node_type == "function_call" and node.name == "N+1 Query Pattern" and _parent_is_loop(node, nodes):
            patterns.append(
                PatternMatch(
                    name="n_plus_one_query_pattern",
                    severity="HIGH",
                    line=node.line_number,
                    explanation="A database or network query is being made inside a loop. This is the N+1 pattern - one query per iteration. For 100 records this means 101 queries. For 10,000 records this is catastrophic.",
                    suggestion="Move the query outside the loop. Fetch all needed data in one call before the loop begins, then access it from memory inside the loop.",
                )
            )
        if node.depth >= 3 and node.node_type in {"data_copy", "memory_alloc"}:
            patterns.append(
                PatternMatch(
                    name="large_object_in_deep_loop",
                    severity="HIGH",
                    line=node.line_number,
                    explanation="An object is being created or copied at a deep nesting level. The cost of this operation multiplies by every outer loop it is inside.",
                    suggestion="Move object creation to the outermost possible scope. Reuse and mutate where your language allows.",
                )
            )

    patterns.extend(_repeated_expensive_calls(nodes))
    return patterns


def _repeated_expensive_calls(nodes: list[SolvixNode]) -> list[PatternMatch]:
    loop_nodes = [node for node in nodes if node.node_type in {"loop", "nested_loop"}]
    matches: list[PatternMatch] = []
    for loop in loop_nodes:
        names = [
            child.name
            for child in loop.children
            if child.node_type == "function_call" and child.name not in {None, "N+1 Query Pattern"}
        ]
        for name, count in Counter(names).items():
            if name and count > 2:
                matches.append(
                    PatternMatch(
                        name="repeated_expensive_function_call",
                        severity="MEDIUM",
                        line=loop.line_number,
                        explanation="The same function is being called repeatedly inside a loop with likely identical or similar arguments. This recalculates what could be computed once.",
                        suggestion="Compute the result once before the loop and store it in a variable. Reference the variable inside the loop.",
                    )
                )
    return matches


def _parent_is_loop(node: SolvixNode, nodes: list[SolvixNode]) -> bool:
    current_parent = node.parent_id
    by_id = {entry.node_id: entry for entry in nodes}
    while current_parent:
        parent = by_id.get(current_parent)
        if not parent:
            return False
        if parent.node_type in {"loop", "nested_loop"}:
            return True
        current_parent = parent.parent_id
    return False
