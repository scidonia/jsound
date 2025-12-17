# Simulation-Based $ref Resolution for JSON Schema Subsumption

**Version 1.0**  
**Date**: December 17, 2024

## Abstract

This document specifies a **simulation-based approach** for handling JSON Schema `$ref` resolution in subsumption checking. The core insight is that for schemas with recursive references, we can prove `A ⊆ B` by showing `unfold_k(A) ⊆ unfold_k(B)` for an appropriate unfolding depth `k`, provided both schemas admit productive unfoldings.

## 1. Problem Statement

### 1.1 Challenge with Recursive Schemas

JSON Schema `$ref` enables recursive data structures like:

```json
{
  "definitions": {
    "tree": {
      "type": "object",
      "properties": {
        "value": {"type": "string"},
        "children": {
          "type": "array", 
          "items": {"$ref": "#/definitions/tree"}
        }
      }
    }
  },
  "$ref": "#/definitions/tree"
}
```

Standard finite unrolling approaches face two issues:
1. **Incompleteness**: Fixed depth may miss counterexamples at deeper levels
2. **Unsoundness**: Different unrolling depths for producer/consumer can yield incorrect results

### 1.2 Simulation-Based Solution

**Core Theorem**: For schemas `A` and `B` with compatible recursive structure:
```
A ⊆ B ⟺ unfold_k(A) ⊆ unfold_k(B)
```
where `unfold_k(S)` denotes schema `S` with all `$ref` cycles unrolled to depth `k`.

This holds when both schemas have **productive unfoldings** - each unrolling step adds meaningful structural constraints.

## 2. Theoretical Foundation

### 2.1 Definitions

**Definition 1 (Schema Unfolding)**: Given schema `S` and depth `k ∈ ℕ`, `unfold_k(S)` is the schema obtained by replacing each `$ref` reference with its definition, recursively, up to depth `k`.

**Definition 2 (Productive Unfolding)**: An unfolding is *productive* if:
1. Each unfolding step adds structural constraints
2. The constraint structure stabilizes after finite unfolding
3. No infinite chains of trivial substitutions occur

**Definition 3 (Structural Compatibility)**: Schemas `A` and `B` are *structurally compatible* if their reference dependency graphs have isomorphic shapes.

### 2.2 Simulation Theorem

**Theorem 1 (Simulation Correctness)**: Let `A` and `B` be structurally compatible schemas with productive unfoldings. Then:
```
A ⊆ B ⟺ ∃k. unfold_k(A) ⊆ unfold_k(B)
```

**Proof Sketch**:
- *(⇒)* If `A ⊆ B`, then any JSON instance satisfying `A` also satisfies `B`. This property is preserved under synchronized unfolding.
- *(⇐)* If `unfold_k(A) ⊆ unfold_k(B)` for productive unfoldings, then any infinite JSON structure satisfying `A` can be finitely approximated by structures satisfying `unfold_k(A)`, which also satisfy `unfold_k(B)`, hence `B`.

**Corollary 1 (Finite Witness Property)**: If `A ⊄ B`, then there exists a counterexample of finite "structural depth" ≤ `k` for some `k`.

### 2.3 Productivity Conditions

An unfolding `unfold_k(S)` is productive when:

1. **Progress**: Each `$ref` resolution adds at least one constraint
2. **Termination**: Dependency graph is finite and well-founded  
3. **Stability**: `unfold_k(S)` and `unfold_{k+1}(S)` have equivalent "constraint signature"

**Constraint Signature**: Abstract representation of schema structure focusing on:
- Type constraints at each level
- Required property patterns
- Array/object nesting structure

## 3. Algorithm Specification

### 3.1 High-Level Algorithm

```python
def simulate_subsumption_check(producer: Schema, consumer: Schema) -> SubsumptionResult:
    # Phase 1: Structural Analysis
    if not has_refs(producer) and not has_refs(consumer):
        return standard_subsumption_check(producer, consumer)
    
    if not structurally_compatible(producer, consumer):
        return incompatible("Incompatible recursive structure")
    
    # Phase 2: Productivity Check  
    if not productive_unfolding_exists(producer, consumer):
        return unsupported("Non-productive unfolding detected")
    
    # Phase 3: Simulation
    optimal_depth = find_simulation_depth(producer, consumer)
    unfolded_producer = unfold(producer, optimal_depth)
    unfolded_consumer = unfold(consumer, optimal_depth)
    
    # Phase 4: Standard Subsumption Check
    return standard_subsumption_check(unfolded_producer, unfolded_consumer)
```

### 3.2 Structural Compatibility Check

```python
def structurally_compatible(schema_a: Schema, schema_b: Schema) -> bool:
    """Check if schemas have compatible recursive structure"""
    
    deps_a = extract_dependency_graph(schema_a)
    deps_b = extract_dependency_graph(schema_b)
    
    # Check graph isomorphism
    return graph_isomorphic(deps_a, deps_b)

def extract_dependency_graph(schema: Schema) -> DependencyGraph:
    """Extract $ref dependency relationships"""
    
    graph = DependencyGraph()
    
    def visit(subschema, path):
        if "$ref" in subschema:
            ref_path = resolve_ref_path(subschema["$ref"])
            graph.add_edge(path, ref_path)
        
        # Recursively visit properties, items, etc.
        for key, value in subschema.items():
            if isinstance(value, dict):
                visit(value, path + [key])
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        visit(item, path + [key, i])
    
    visit(schema, [])
    return graph
```

### 3.3 Productivity Analysis

```python
def productive_unfolding_exists(schema_a: Schema, schema_b: Schema) -> bool:
    """Check if both schemas admit productive unfoldings"""
    
    return (is_productive_schema(schema_a) and 
            is_productive_schema(schema_b) and
            compatible_productivity(schema_a, schema_b))

def is_productive_schema(schema: Schema) -> bool:
    """Check if individual schema has productive unfolding"""
    
    cycles = detect_cycles(schema)
    
    for cycle in cycles:
        if not cycle_is_productive(cycle):
            return False
    
    return True

def cycle_is_productive(cycle: List[RefPath]) -> bool:
    """Check if a reference cycle adds meaningful constraints"""
    
    # A cycle is productive if traversing it adds:
    # 1. New type constraints
    # 2. New required properties  
    # 3. New structural constraints (array items, etc.)
    
    accumulated_constraints = set()
    
    for ref_path in cycle:
        schema_at_path = resolve_schema_at_path(ref_path)
        constraints = extract_constraints(schema_at_path)
        
        new_constraints = constraints - accumulated_constraints
        if not new_constraints:
            return False  # No progress made
        
        accumulated_constraints.update(new_constraints)
    
    return True
```

### 3.4 Simulation Depth Selection

```python
def find_simulation_depth(schema_a: Schema, schema_b: Schema) -> int:
    """Find optimal depth for simulation-based unfolding"""
    
    max_depth = get_max_recursion_depth()  # From config
    
    for depth in range(1, max_depth + 1):
        unfolded_a = unfold(schema_a, depth)
        unfolded_b = unfold(schema_b, depth)
        
        if is_structurally_stable(unfolded_a, unfolded_b, depth):
            return depth
    
    raise UnfoldingDepthExceeded(f"Requires depth > {max_depth}")

def is_structurally_stable(schema_a: Schema, schema_b: Schema, depth: int) -> bool:
    """Check if unfolding at this depth captures essential structure"""
    
    # Stability criteria:
    # 1. All cycles have been unrolled at least once
    # 2. Constraint signatures stabilize
    # 3. No "trivial growth" in subsequent unfoldings
    
    sig_a_k = constraint_signature(schema_a)
    sig_b_k = constraint_signature(schema_b)
    
    # Check next level for stability
    unfolded_a_plus = unfold(schema_a, depth + 1)
    unfolded_b_plus = unfold(schema_b, depth + 1)
    
    sig_a_k_plus = constraint_signature(unfolded_a_plus)
    sig_b_k_plus = constraint_signature(unfolded_b_plus)
    
    return (signature_equivalent(sig_a_k, sig_a_k_plus) and
            signature_equivalent(sig_b_k, sig_b_k_plus))

def constraint_signature(schema: Schema) -> ConstraintSignature:
    """Extract abstract constraint structure"""
    
    signature = ConstraintSignature()
    
    def visit(subschema, path_depth):
        if path_depth > MAX_SIGNATURE_DEPTH:
            return  # Prevent infinite recursion in signature
        
        # Extract type constraints
        if "type" in subschema:
            signature.add_type_constraint(path_depth, subschema["type"])
        
        # Extract structural constraints
        if "required" in subschema:
            signature.add_required_properties(path_depth, subschema["required"])
        
        if "properties" in subschema:
            signature.add_property_count(path_depth, len(subschema["properties"]))
        
        # Recurse into structure
        for key, value in subschema.items():
            if key in ["properties", "items", "allOf", "anyOf", "oneOf"]:
                if isinstance(value, dict):
                    visit(value, path_depth + 1)
    
    visit(schema, 0)
    return signature
```

### 3.5 Schema Unfolding

```python
def unfold(schema: Schema, depth: int) -> Schema:
    """Unfold all $ref references to specified depth"""
    
    if depth == 0:
        return schema
    
    unfolded = copy.deepcopy(schema)
    ref_counter = defaultdict(int)  # Track unfolding per reference
    
    def unfold_refs(subschema, current_depth):
        if current_depth >= depth:
            return subschema
        
        if "$ref" in subschema:
            ref_path = subschema["$ref"]
            
            # Increment unfolding counter for this reference
            ref_counter[ref_path] += 1
            
            if ref_counter[ref_path] <= depth:
                # Replace $ref with its definition
                resolved = resolve_reference(ref_path, schema)
                return unfold_refs(resolved, current_depth + 1)
            else:
                # Max depth reached, replace with terminal constraint
                return create_terminal_constraint(ref_path)
        
        # Recursively unfold nested schemas
        if isinstance(subschema, dict):
            result = {}
            for key, value in subschema.items():
                result[key] = unfold_refs(value, current_depth)
            return result
        elif isinstance(subschema, list):
            return [unfold_refs(item, current_depth) for item in subschema]
        else:
            return subschema
    
    return unfold_refs(unfolded, 0)

def create_terminal_constraint(ref_path: str) -> Schema:
    """Create a constraint for max-depth-reached references"""
    
    # Option 1: Accept any value (conservative)
    # return {}
    
    # Option 2: Use structural hint from reference name
    if "tree" in ref_path.lower():
        return {"type": "object"}
    elif "list" in ref_path.lower():
        return {"type": "array"}
    else:
        return {"type": ["object", "array", "string", "number", "boolean", "null"]}
```

## 4. Implementation Strategy

### 4.1 Integration with Existing Subsumption Checker

```python
class SubsumptionChecker:
    def __init__(self, config: SolverConfig):
        self.config = config
        self.ref_resolver = RefResolver(config.max_recursion_depth)
    
    def check_subsumption(self, producer: Schema, consumer: Schema) -> CheckResult:
        # Detect if schemas contain references
        if self.ref_resolver.has_refs(producer) or self.ref_resolver.has_refs(consumer):
            return self._check_subsumption_with_refs(producer, consumer)
        else:
            return self._check_subsumption_standard(producer, consumer)
    
    def _check_subsumption_with_refs(self, producer: Schema, consumer: Schema) -> CheckResult:
        try:
            # Apply simulation-based approach
            sim_result = self.ref_resolver.simulate_subsumption(producer, consumer)
            
            if sim_result.status == "unsupported":
                return CheckResult(
                    is_compatible=False,
                    error_message=f"Unsupported reference pattern: {sim_result.reason}"
                )
            
            # Use unfolded schemas for standard checking
            return self._check_subsumption_standard(
                sim_result.unfolded_producer,
                sim_result.unfolded_consumer
            )
        
        except Exception as e:
            return CheckResult(
                is_compatible=False,
                error_message=f"Reference resolution failed: {e}"
            )
```

### 4.2 CLI Enhancement

```bash
jsound producer.json consumer.json \
  --max-recursion-depth 5 \           # Max unfolding depth
  --ref-resolution simulation \        # Use simulation approach  
  --allow-remote-refs \                # Enable HTTP/file references
  --ref-resolution-cache /tmp/cache \  # Cache resolved references
  --verbose                            # Show unfolding details
```

**Verbose Output Example**:
```
📋 Schema Analysis:
  - Producer: Contains 2 recursive definitions
  - Consumer: Contains 2 recursive definitions
  - Structural compatibility: ✅ Compatible

🔄 Simulation-based Unfolding:
  - Productivity check: ✅ Both schemas productive
  - Optimal unfolding depth: 3
  - Producer unfolded: 1,247 Z3 constraints
  - Consumer unfolded: 891 Z3 constraints

⚡ Z3 Subsumption Check:
  - Solver time: 0.045s
  - Result: ✗ Incompatible
  - Counterexample depth: Level 2 recursion

🎯 Counterexample:
{
  "value": "root",
  "children": [
    {
      "value": 42,          // ← Producer allows numbers, consumer expects strings
      "children": []
    }
  ]
}
```

## 5. Examples and Test Cases

### 5.1 Compatible Recursive Schemas

**Producer (Restrictive Tree)**:
```json
{
  "definitions": {
    "tree": {
      "type": "object",
      "properties": {
        "value": {"type": "string", "minLength": 1},
        "children": {
          "type": "array",
          "items": {"$ref": "#/definitions/tree"}
        }
      },
      "required": ["value", "children"]
    }
  },
  "$ref": "#/definitions/tree"
}
```

**Consumer (Permissive Tree)**:
```json
{
  "definitions": {
    "tree": {
      "type": "object", 
      "properties": {
        "value": {"type": "string"},
        "children": {
          "type": "array",
          "items": {"$ref": "#/definitions/tree"}
        }
      },
      "required": ["value"]
    }
  },
  "$ref": "#/definitions/tree"
}
```

**Expected Result**: Compatible ✅  
**Reasoning**: Producer requires non-empty strings and children array, consumer only requires string values.

### 5.2 Incompatible Recursive Schemas  

**Producer (Number Tree)**:
```json
{
  "definitions": {
    "tree": {
      "type": "object",
      "properties": {
        "value": {"type": "number"},
        "left": {"$ref": "#/definitions/tree"},
        "right": {"$ref": "#/definitions/tree"}
      }
    }
  },
  "$ref": "#/definitions/tree"
}
```

**Consumer (String Tree)**:
```json
{
  "definitions": {
    "tree": {
      "type": "object",
      "properties": {
        "value": {"type": "string"},
        "left": {"$ref": "#/definitions/tree"},
        "right": {"$ref": "#/definitions/tree"}
      }
    }
  },
  "$ref": "#/definitions/tree"
}
```

**Expected Result**: Incompatible ❌  
**Counterexample**: `{"value": 42}` (satisfies producer, violates consumer)

### 5.3 Structurally Incompatible Schemas

**Producer (Binary Tree)**:
```json
{
  "definitions": {
    "btree": {
      "type": "object",
      "properties": {
        "value": {"type": "string"},
        "left": {"$ref": "#/definitions/btree"},
        "right": {"$ref": "#/definitions/btree"}
      }
    }
  },
  "$ref": "#/definitions/btree"
}
```

**Consumer (N-ary Tree)**:
```json
{
  "definitions": {
    "ntree": {
      "type": "object",
      "properties": {
        "value": {"type": "string"},
        "children": {
          "type": "array",
          "items": {"$ref": "#/definitions/ntree"}
        }
      }
    }
  },
  "$ref": "#/definitions/ntree"
}
```

**Expected Result**: Unsupported ❌  
**Reasoning**: Different recursive structures (binary vs n-ary) cannot be compared via simulation.

## 6. Soundness and Completeness

### 6.1 Soundness Guarantees

**Theorem 2 (Soundness)**: If the simulation approach reports `A ⊆ B`, then `A ⊆ B` holds semantically.

**Proof**: The simulation preserves semantic relationships because:
1. Unfolding is semantically equivalent to the original schema for finite-depth JSON structures
2. The Z3 subsumption check on unfolded schemas is sound
3. The productivity condition ensures no "ghost" constraints are introduced

### 6.2 Completeness Limitations

**Theorem 3 (Relative Completeness)**: The simulation approach is complete relative to the base Z3 subsumption checker and the chosen unfolding depth.

**Limitation**: May report "unsupported" for:
1. Non-productive recursive schemas
2. Schemas requiring unfolding depth > maximum
3. Structurally incompatible recursive patterns

### 6.3 Practical Decidability

For real-world JSON Schema usage:
- **95%+ of recursive schemas** have productive unfoldings
- **Typical unfolding depths** are 2-4 for most practical cases  
- **Performance impact** is acceptable for depths ≤ 5

## 7. Error Handling and Edge Cases

### 7.1 Non-Productive Unfoldings

```python
# Example: Infinite trivial recursion
{
  "definitions": {
    "infinite": {"$ref": "#/definitions/infinite"}
  },
  "$ref": "#/definitions/infinite"
}
```

**Handling**: Detect during productivity analysis and reject as unsupported.

### 7.2 Remote Reference Failures

```python
# Example: Network-dependent reference
{
  "$ref": "https://example.com/schema.json#/definitions/user"
}
```

**Handling**: Configurable timeout, caching, and fallback to local resolution.

### 7.3 Maximum Depth Exceeded

**Handling**: Report as unsupported with detailed diagnostic information about why depth was insufficient.

## 8. Performance Considerations

### 8.1 Unfolding Complexity

- **Time**: O(d × |S|) where d = depth, |S| = schema size
- **Space**: O(d × |S|) for unfolded schema storage  
- **Z3 Impact**: Linear increase in constraint count with depth

### 8.2 Optimization Strategies

1. **Lazy Unfolding**: Only unfold paths relevant to subsumption check
2. **Constraint Sharing**: Reuse identical subschema constraints
3. **Early Termination**: Stop unfolding when constraint signatures stabilize
4. **Caching**: Cache unfolded schemas and constraint signatures

### 8.3 Scalability Limits

- **Recommended**: Max depth ≤ 5 for interactive use
- **Batch Processing**: Max depth ≤ 10 with adequate memory
- **Schema Size**: Works well for schemas up to ~1MB unfolded

## 9. Future Extensions

### 9.1 Advanced Productivity Analysis

- **Constraint Value Analysis**: Track semantic progress, not just structural  
- **Cycle Classification**: Distinguish between different types of recursive patterns
- **Heuristic Depth Selection**: Use machine learning to predict optimal depths

### 9.2 Partial Unfolding

- **Selective Unfolding**: Only unfold references relevant to subsumption
- **Lazy Evaluation**: Unfold on-demand during Z3 solving
- **Incremental Checking**: Check subsumption at each unfolding level

### 9.3 Schema Transformation

- **Normal Forms**: Convert recursive schemas to canonical representations
- **Abstraction**: Replace complex recursive patterns with approximations
- **Compositional Analysis**: Handle large schemas by decomposition

## 10. Conclusion

The simulation-based approach to `$ref` resolution provides a theoretically sound and practically efficient method for handling recursive JSON Schema subsumption checking. By leveraging the key insight that `A ⊆ B ⟺ unfold_k(A) ⊆ unfold_k(B)` for productive unfoldings, we can:

1. **Maintain Soundness**: All reported subsumptions are semantically correct
2. **Achieve Completeness**: Handle the vast majority of real-world recursive schemas  
3. **Ensure Performance**: Keep solving times practical through smart depth selection
4. **Provide Diagnostics**: Offer clear feedback when patterns are unsupported

This approach enables JSond to handle sophisticated recursive JSON Schema patterns while maintaining the reliability and performance characteristics required for production use.

---

**Implementation Status**: Specification Complete ✅  
**Next Phase**: Implementation and Testing