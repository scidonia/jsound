# Making Z3 Counterexamples Informative for JSON-Schema Subsumption (`P ∧ ¬C`)
**Guidance note — v0.2**

You already have the right *logical* check (`P ⊆ C` via `P(x) ∧ ¬C(x)`), and Z3 is returning `sat`.
The remaining problem is **explanation and reconstruction**: the model is *underspecified* (uninterpreted arrays, defaults),
so your JSON printer emits a vague `{ "sample": "value" }`.

This note gives concrete techniques (Python + `z3-solver`) to answer:

- **What exactly in `C` fails?**
- **Which field/path causes incompatibility?**
- **How do we print a meaningful witness?**
- **How do we shrink/minimize counterexamples?**

---

## 1) Why you’re seeing `{ "sample": "value" }`

From your trace, the *real* constraints mention `"contact"` and regexes.
Yet the model dump shows:

```
Z3 Model (raw):
[x = obj(7),
 has = ,
 val = ]
```

This typically means:
- `has` and `val` are **uninterpreted arrays** (no concrete entries printed),
- you reconstruct JSON without querying `has(x,k)` / `val(x,k)` carefully,
- Z3 leaves most array entries **as “else/default”**, and your printer invents arbitrary key/value pairs.

**Fix:** reconstruction must be **model-driven** and based on your chosen `Keys` universe and/or `required/properties`,
not based on “pick any key/value”.

---

## 2) Model completion: always evaluate with defaults

When reading from a model, always use:

```python
m.eval(expr, model_completion=True)
```

This forces Z3 to give a concrete value even for “unspecified” entries (using the model’s `else` values).

Example:

```python
present = m.eval(has(x, "contact"), model_completion=True)
v = m.eval(val(x, "contact"), model_completion=True)
```

If you don’t do this, you’ll often get “nothing” for arrays and your JSON printer will guess.

---

## 3) Deterministic JSON reconstruction (don’t invent keys)

### 3.1 Use a finite key universe
Maintain a **finite `Keys` set** for your run:
- union of all `properties` keys across both schemas (and optionally a test suite)
- optionally include a small “extra keys” set only if `additionalProperties` is allowed

### 3.2 Emit exactly those keys whose `has(x,k)` is true
Pseudocode:

```python
def materialize_object(m, x, Keys):
    out = {}
    for k in Keys:
        if z3.is_true(m.eval(has(x, k), model_completion=True)):
            out[k] = materialize_json(m, m.eval(val(x, k), model_completion=True))
    return out
```

If your producer schema requires `"contact"`, `has(x,"contact")` **must** come out `true` and it will show up.

### 3.3 If `additionalProperties: false`, never print keys outside `properties`
If `additionalProperties` is `false`, any extra key is invalid. Don’t output `"sample"`.

---

## 4) “Where does it fail?”: label every constraint and evaluate it

For `sat`, there’s no unsat core. Instead:
- attach **named labels** to constraints,
- after `sat`, evaluate which labels are **true/false** in the witness.

### 4.1 Labeling pattern
When compiling, return a pair:
- `formula`
- `explanations: dict[label -> BoolRef]`

Each label is a Z3 Bool you assert equivalence to the underlying constraint.

Example helper:

```python
def label(lbl, c, labels):
    b = z3.Bool(lbl)
    labels[lbl] = b
    return b == c
```

Now in compilation:

```python
labels = {}
consumer_formula = z3.And(
    label("C:type:object", is_obj(x), labels),
    label("C:req:contact", has(x,"contact"), labels),
    label("C:contact:pattern:url_or_ftp",
          z3.Or(InRe(str_val(val(x,"contact")), re_http),
                InRe(str_val(val(x,"contact")), re_ftp)),
          labels),
)
```

After `sat`, evaluate:

```python
for name, b in labels.items():
    print(name, m.eval(b, model_completion=True))
```

You’ll immediately see **which consumer labels are false** under the witness.
That gives you an explanation like:

- `C:contact:pattern:url_or_ftp = false`
- while producer’s email pattern label is true

### 4.2 Prefer path-like labels
Use labels like:
- `C:/contact/pattern/url`
- `C:/contact/pattern/ftp`
- `P:/contact/pattern/email`

This naturally points to the **field/path** causing incompatibility.

---

## 5) Produce a human explanation from labels

Once you know which consumer constraints fail, map them back to schema keywords:

Example report:

- Witness satisfies producer because `/contact` matches email regex.
- Witness violates consumer because `/contact` does not match URL or FTP regex.
- Therefore, producer allows emails but consumer expects URLs.

This is much more actionable than a raw JSON blob.

---

## 6) Counterexample minimization (make witnesses smaller)

Z3 models can be weird even when correct. You can **shrink** witnesses with an optimization loop.

### 6.1 MaxSMT / Optimize approach (easy wins)
Use `z3.Optimize()` and add soft constraints like:
- minimize array lengths
- minimize string lengths
- minimize number of present keys
- prefer empty objects unless required

Sketch:

```python
opt = z3.Optimize()
opt.add(P(x), z3.Not(C(x)))

# Soft preferences:
for k in Keys:
    opt.add_soft(z3.Not(has(x,k)), weight=1)      # fewer keys
# Example objective if you have a string variable s:
# opt.minimize(z3.Length(s))

opt.check()
m = opt.model()
```

This often converts “random junk” witnesses into the simplest failing witness.

### 6.2 Delta-debugging minimization (robust, slower)
Given a witness JSON, iteratively try:
- remove optional keys
- shorten strings
- replace nested objects with `{}`
- shrink arrays
and re-check `P ∧ ¬C` with the candidate pinned as a concrete value.

This is solver-driven “ddmin” and yields very clean repros.

---

## 7) Concretize strings for readability

If Z3 gives an abstract string that still satisfies constraints, it might be long/ugly.
You can **guide** it to pick nicer ones by adding preferences:

- `Length(s) <= 32`
- restrict alphabet for printing (e.g., `[a-zA-Z0-9._-]`)
- add soft constraints on length

If you use regex constraints, Z3 can still produce concrete matches; but *without* length bounds,
it may choose arbitrary length.

---

## 8) A concrete “why incompatible” workflow

When you run `P ∧ ¬C` and it is SAT:

1. **Reconstruct witness** using `Keys` and `model_completion=True`.
2. **Evaluate labeled constraints** for both `P` and `C` under the model.
3. Print a small report:
   - the first failing consumer label(s),
   - the relevant producer label(s) that allowed it,
   - the witness value for those paths (e.g., `/contact = "a@bcd.e"`).

This answers “where will I have problems?” as a path-based diff.

---

## 9) Quick sanity checks for your current output

Given your producer requires `"contact"`, but the JSON printed shows `"sample"`:

- Ensure your printer only emits keys `k` where `has(x,k)` is true.
- Ensure you included `"contact"` in `Keys`.
- Ensure you call `m.eval(has(x,"contact"), model_completion=True)`.
- Ensure you do **not** fabricate keys/values when the model is silent.

Once fixed, you should see a witness like:

```json
{ "contact": "a@bcd.e" }
```

(or similar), which will clearly violate the consumer’s URL/FTP patterns.

---

## 10) Optional: show the first failing consumer disjunct for `oneOf/anyOf`

For `anyOf`, `oneOf`, and `if/then/else`, your labels should include:
- each branch predicate
- the cardinality checks (for `oneOf`)

Then in explanations you can show:
- which branches were true/false
- why `oneOf` failed (0 branches or ≥2 branches)

This prevents “it failed somewhere in oneOf” vagueness.

---

**End of guidance note**
