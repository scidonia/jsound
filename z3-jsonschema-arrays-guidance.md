# Implementing JSON Schema Array Semantics in Z3 (Python)
**Guidance note (arrays, `items`, subsumption checks) — v0.1**

This document explains **how to correctly encode JSON Schema array constraints** into Z3 using **Python + `z3-solver`**, with a focus on:
- `items` (element constraints)
- `minItems` / `maxItems`
- subsumption checks via `P ∧ ¬C`
- practical, solver-friendly approaches (bounded, quantifier-free)

---

## 1) The core mistake to avoid

> **Wrong:** applying `items` constraints to the *array value itself*  
> **Right:** applying `items` constraints to *each element* of the array

For schema:

```json
{ "type": "array", "items": S }
```

The meaning is:

> `j` is an array, and **for every in-bounds index** `i`, `j[i]` satisfies `S`.

Formally:

```
is_array(j) ∧ ∀i. (0 ≤ i < len(j)) → Sat(S, elem(j,i))
```

That’s why tests like:
- `string_array` should **not** be subsumed by `number_array`

are supposed to fail: a witness like `["x"]` exists.

---

## 2) Recommended encoding: bounded, quantifier-free arrays

Quantifiers are possible but often slow and brittle with recursive predicates.
For message schemas and LSP-style tests, the best engineering choice is:

- Choose a constant `MAX_ARRAY_LEN = L`
- Represent an array as:
  - `len : Int`
  - `elems : Array[Int, JSON]`
- Add constraint: `0 ≤ len ≤ L`
- Encode `items` by **unrolling** `i = 0..L-1`:
  - `Implies(i < len, Sat(items_schema, elems[i]))`

This is **correct within the bound** and gives excellent counterexamples.

### Why this works for subsumption checks
To prove `P ⊆ C`, solve:

```
Sat(P, x) ∧ ¬Sat(C, x)
```

- `sat` ⇒ counterexample instance `x`
- `unsat` ⇒ subsumption holds (within your bounds)

For `P = array of strings` and `C = array of numbers`, Z3 can satisfy the formula by choosing:
- `len = 1`
- element 0 = `"x"`
which satisfies `P` but violates `C`.

---

## 3) Minimal Python/Z3 skeleton for arrays

Below is a minimal sketch focusing on arrays. You’ll integrate this into your full `Sat(schema, j)` compiler.

### 3.1 JSON value model (array portion)
Many implementations use a tagged datatype for JSON. Here we assume you already have:
- `is_arr(j)`  — predicate “j is an array JSON value”
- `arr_len(j)` — returns length Int
- `arr_elems(j)` — returns `Array(Int, JSON)`

If you don’t yet have a JSON datatype, you can prototype with separate variables
for length+elements, but the general encoding is the same.

### 3.2 Compile rule for `type: "array"`
```python
def sat_type_array(j):
    return is_arr(j)
```

### 3.3 Compile rules for `minItems` / `maxItems`
```python
def sat_min_items(j, m):
    return z3.Implies(is_arr(j), arr_len(j) >= m)

def sat_max_items(j, n):
    return z3.Implies(is_arr(j), arr_len(j) <= n)
```

### 3.4 Compile rule for `items: S` (single-schema form)
```python
import z3

MAX_ARRAY_LEN = 8  # choose per project / test suite

def sat_items(j, item_schema, sat_schema_fn):
    \"\"\"
    sat_schema_fn(schema, json_value) -> z3 BoolRef
    \"\"\"
    i_constraints = []
    for i in range(MAX_ARRAY_LEN):
        i_constraints.append(
            z3.Implies(
                z3.And(is_arr(j), i < arr_len(j)),
                sat_schema_fn(item_schema, z3.Select(arr_elems(j), i))
            )
        )
    # also enforce bounded length
    bounds = z3.Implies(is_arr(j), z3.And(arr_len(j) >= 0, arr_len(j) <= MAX_ARRAY_LEN))
    return z3.And(bounds, *i_constraints)
```

#### Key points
- The `i < arr_len(j)` guard is essential.
- Add `0 ≤ len ≤ MAX_ARRAY_LEN` so the model doesn’t pick arbitrarily large `len`.
- Make the whole thing conditional on `is_arr(j)` if you allow schemas that omit `"type":"array"` but still include array keywords.

---

## 4) Tuple validation / prefix items (common “standard” extension)

JSON Schema has two common patterns depending on draft:
- Older: `"items": [S0,S1,...]` plus `additionalItems`
- Draft 2020-12: `prefixItems` plus `items` for the rest

You can encode tuple validation without quantifiers using the same bound `L`.

### 4.1 Draft-2020-12 style: `prefixItems` + `items`
Example:
```json
{
  "type": "array",
  "prefixItems": [S0, S1],
  "items": Srest
}
```

Encoding:
- If `len >= 1`, element 0 satisfies `S0`
- If `len >= 2`, element 1 satisfies `S1`
- For indices `i >= 2`, element i satisfies `Srest`

Python sketch:
```python
def sat_prefix_items(j, prefix_schemas, rest_schema, sat_schema_fn):
    cs = []
    for idx, sch in enumerate(prefix_schemas):
        cs.append(
            z3.Implies(
                z3.And(is_arr(j), idx < arr_len(j)),
                sat_schema_fn(sch, z3.Select(arr_elems(j), idx))
            )
        )
    if rest_schema is not None:
        for i in range(len(prefix_schemas), MAX_ARRAY_LEN):
            cs.append(
                z3.Implies(
                    z3.And(is_arr(j), i < arr_len(j)),
                    sat_schema_fn(rest_schema, z3.Select(arr_elems(j), i))
                )
            )
    else:
        # "no extra items allowed"
        cs.append(z3.Implies(is_arr(j), arr_len(j) <= len(prefix_schemas)))

    bounds = z3.Implies(is_arr(j), z3.And(arr_len(j) >= 0, arr_len(j) <= MAX_ARRAY_LEN))
    return z3.And(bounds, *cs)
```

---

## 5) When (not) to use quantifiers

### 5.1 Quantified encoding (unbounded arrays)
The mathematically direct encoding is:

```python
i = z3.Int('i')
z3.ForAll(i, z3.Implies(z3.And(0 <= i, i < arr_len(j)), sat(item_schema, z3.Select(elems,i))))
```

### 5.2 Practical issues
- `sat(item_schema, ...)` is recursive and can include other arrays/objects/conditionals.
- Z3 may struggle to instantiate quantifiers effectively.
- Performance and completeness can suffer.

### 5.3 Recommendation
Use quantifiers only if you have a strong need for unbounded reasoning and you’re prepared to:
- restrict the schema fragment, and/or
- carefully manage triggers, and/or
- accept slower solving.

For message pipelines, bounded unrolling is usually the right trade-off.

---

## 6) Subsumption test harness (array example)

Given `P` and `C`, check compatibility by solving:

```
Sat(P, x) ∧ ¬Sat(C, x)
```

Python sketch:

```python
def check_subsumed(schema_P, schema_C, sat_schema_fn, x):
    s = z3.Solver()
    s.add(sat_schema_fn(schema_P, x))
    s.add(z3.Not(sat_schema_fn(schema_C, x)))
    r = s.check()
    return r, s.model() if r == z3.sat else None
```

Expected behavior:
- `sat` ⇒ **NOT subsumed** (incompatible), and model contains a witness
- `unsat` ⇒ **subsumed** (compatible) under your bounds

---

## 7) Witness extraction guidance (arrays)
To turn a SAT model into JSON:

1. Read `len = model.eval(arr_len(x))`
2. For `i in 0..len-1`:
   - read `model.eval(Select(arr_elems(x), i))`
3. Recursively decode element JSON values using your JSON datatype constructors

If your `JSON` is a Z3 `Datatype`, use:
- `is_<Constructor>(j)` tests
- accessors (e.g., `Str.s(j)` or similar depending on how you declared the datatype)

---

## 8) Common gotchas checklist
- [ ] `items` constraints apply to **elements**, not the array node
- [ ] Guard element constraints with `i < len`
- [ ] Bound `len` (and keep it non-negative)
- [ ] For tuple/prefix items, encode both fixed positions and rest
- [ ] Keep subsumption check as `P ∧ ¬C` and extract witnesses on SAT
- [ ] If you must support `contains`, it’s `∃i < len` not `∀i < len`

---

## 9) Recommended configuration defaults
- `MAX_ARRAY_LEN`: start with 8–16 for tests; increase if needed
- Require schemas to be within a “pipeline-safe fragment”:
  - arrays bounded, objects keys from known universe
  - avoid deep recursion unless you unroll `$ref` to a depth

---

**End of guidance note**
