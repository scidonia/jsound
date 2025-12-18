# JSON Schema → SMT (Z3) Subsumption Checker
**Specification v0.1**

This document specifies how to build an agent/library that checks **schema subsumption**
between JSON Schemas using an **SMT solver (Z3)**.

The primary judgment is:

> **Producer schema P is compatible with consumer schema C iff**
>
> `P ⊆ C`
>
> which is decided by checking:
>
> `P ∧ ¬C` is **UNSAT**

If SAT, the solver must return a **counterexample JSON instance**.

---

## 1. Goals and Non‑Goals

### Goals
- Decide schema subsumption using SMT (Z3)
- Produce concrete counterexample JSON instances
- Support a large, practical subset of JSON Schema
- Be usable in message-passing / pipeline systems

### Non‑Goals
- Full support for all JSON Schema drafts without restriction
- Unbounded reasoning over arbitrary object keys or array lengths
- Perfect ECMAScript regex compatibility (subset allowed)

---

## 2. Target JSON Schema Features

The agent **MUST** support:

### Core
- `type` (single or array)
- `const`
- `enum`
- Boolean composition:
  - `allOf`
  - `anyOf`
  - `oneOf`
  - `not`

### Objects
- `properties`
- `required`
- `additionalProperties`
- `patternProperties`
- `$ref`

### Arrays
- `items` (single schema)
- `minItems`
- `maxItems`

### Conditionals
- `if` / `then` / `else`

### Numbers
- `integer`
- `number`
- `minimum`
- `maximum`
- `exclusiveMinimum`
- `exclusiveMaximum`
- `multipleOf`

### Strings
- `minLength`
- `maxLength`
- `pattern`

---

## 3. Semantic Strategy

### Subsumption
Given schemas **P** and **C**, subsumption is checked by:

```
SAT( P(x) ∧ ¬C(x) ) ? incompatible : compatible
```

### Witness
If SAT, the solver model **must be convertible into a concrete JSON value**.

---

## 4. JSON Value Encoding in Z3

### 4.1 JSON Datatype

The agent **MUST** define a tagged union:

```
JSON =
  Null
| Bool(b: Bool)
| Int(n: Int)
| Real(r: Real)
| Str(s: String)
| Arr(len: Int, elems: Array[Int, JSON])
| Obj(has: Array[String, Bool],
      val: Array[String, JSON])
```

### 4.2 Type Predicates
For each constructor, define:
- `is_null(j)`
- `is_bool(j)`
- `is_int(j)`
- `is_real(j)`
- `is_str(j)`
- `is_arr(j)`
- `is_obj(j)`

Exactly **one** must hold for any JSON value.

---

## 5. Finite Universes and Bounds

To remain decidable and performant, the agent **MUST** choose:

### 5.1 Key Universe
A finite set:

```
Keys = union of all property names appearing in any schema
```

Used to eliminate quantifiers for object reasoning.

### 5.2 Array Length Bound
A constant `MAX_ARRAY_LEN`.
Array constraints are unrolled for indices `0 .. MAX_ARRAY_LEN-1`.

### 5.3 Recursion / $ref Depth
- `$ref` MUST be resolved
- Cycles MUST be unrolled to a fixed depth or rejected

---

## 6. Schema Compilation Rules

Let `⟦S⟧(j)` denote the Z3 predicate “JSON value `j` satisfies schema `S`”.

### 6.1 type
```
"type": "object" → is_obj(j)
"type": ["string","null"] → is_str(j) ∨ is_null(j)
```

### 6.2 const / enum
```
const: v → j == encode(v)
enum: [v1..vn] → (j == v1 ∨ ... ∨ j == vn)
```

### 6.3 allOf / anyOf / oneOf
```
allOf → ∧ ⟦Si⟧(j)
anyOf → ∨ ⟦Si⟧(j)
oneOf → exactly-one(⟦Si⟧(j))
```

`oneOf` MUST enforce **at most one** and **at least one**.

### 6.4 not
```
not: S → ¬⟦S⟧(j)
```

---

## 7. Object Keywords

### 7.1 required
For each `k ∈ required`:
```
is_obj(j) → has(j,k)
```

### 7.2 properties
For each property `k` with schema `Sk`:
```
has(j,k) → ⟦Sk⟧(val(j,k))
```

### 7.3 additionalProperties
If `false`:
```
∀ k ∈ Keys \ declared:
  has(j,k) == false
```

If schema `S`:
```
has(j,k) ∧ k not declared → ⟦S⟧(val(j,k))
```

### 7.4 patternProperties
Each pattern `p` is compiled to a Z3 regex `Rp`.

For every `k ∈ Keys`:
```
InRe(k, Rp) ∧ has(j,k) → ⟦Sp⟧(val(j,k))
```

Overlapping patterns are **conjunctive**, per JSON Schema semantics.

---

## 8. Arrays

### 8.1 Length
```
minItems ≤ len ≤ maxItems
```

### 8.2 items
For each index `i`:
```
i < len → ⟦S⟧(elems[i])
```

---

## 9. Conditionals (if / then / else)

```
if: Si
then: St
else: Se
```

Compiles as:

```
(⟦Si⟧(j) → ⟦St⟧(j)) ∧ (¬⟦Si⟧(j) → ⟦Se⟧(j))
```

If `then` or `else` is absent, that branch is `true`.

---

## 10. Numbers

### 10.1 integer
```
is_int(j)
```

### 10.2 number
```
is_int(j) ∨ is_real(j)
```

### 10.3 bounds
```
minimum → n ≥ m
exclusiveMinimum → n > m
maximum → n ≤ m
exclusiveMaximum → n < m
```

### 10.4 multipleOf
For integers:
```
n mod k == 0
```

For reals:
- MUST be approximated or restricted
- RECOMMENDED: restrict `multipleOf` to integers only

---

## 11. Strings

### 11.1 Length
```
minLength ≤ Length(s) ≤ maxLength
```

### 11.2 pattern
- Convert ECMA regex to Z3 regex subset
- Assert: `InRe(s, R)`

Unsupported regex features MUST be rejected or approximated conservatively.

---

## 12. $ref Handling

- `$ref` MUST be resolved before compilation
- Remote refs MAY be cached or rejected
- Cycles MUST be:
  - bounded by unrolling depth, or
  - rejected as unsupported

---

## 13. Solver Invocation

To check `P ⊆ C`:

```
declare JSON x
assert ⟦P⟧(x)
assert ¬⟦C⟧(x)
check-sat
```

- `sat` → incompatible (extract witness)
- `unsat` → compatible

---

## 14. Model → JSON Reconstruction

The agent MUST be able to:
- Inspect constructor tags
- Decode object keys via `has`
- Recursively reconstruct children
- Emit a valid JSON instance

This instance is the **counterexample message**.

---

## 15. Soundness Notes

- Results are sound **within chosen bounds**
- Increasing bounds monotonically increases precision
- UNSAT implies subsumption under the configured profile

---

## 16. Future Extensions

- `contains`
- `dependentSchemas`
- `unevaluatedProperties`
- SMT-LIB backend
- Proof artifact export

---

**End of Specification**
