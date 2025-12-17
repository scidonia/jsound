# Coinductive Subsumption for Recursive JSON Schemas

## 1. Purpose

This document defines a **sound and clean theoretical foundation** for subsumption
(consumer–producer compatibility) of recursive JSON Schemas.

It is intended to serve as the authoritative guide for implementations based on
unfolding, simulation, and SMT solving.

The central idea is:

> **Subsumption is a coinductive simulation.**
> Unfolding preserves subsumption, independently of algorithmic concerns.

---

## 2. Semantic Model

### 2.1 Schemas as Predicates

A JSON Schema `S` denotes a predicate over JSON values:

    ⟦S⟧ : JSON → Bool

Recursive schemas may denote infinite objects, but always define a predicate.

### 2.2 The Subsumption Relation

Schema `A` is subsumed by schema `B`, written:

    A <| B

iff every value accepted by `A` is also accepted by `B`:

    ∀v. ⟦A⟧(v) ⇒ ⟦B⟧(v)

This definition is semantic and independent of how schemas are represented.

---

## 3. One-Step Schema Structure

### 3.1 Structural Constructors

A schema exposes one outer *constructor layer*, such as:

* `type`
* `object` with `properties` / `patternProperties`
* `array` with `items`
* `oneOf`, `anyOf`, `allOf`
* `if / then / else`
* `$ref`

### 3.2 One-Step Unfolding

Define a **one-step unfolding operator** `U(S)`:

* If `S` is not a `$ref`, then `U(S) = S`
* If `S` is `$ref: X`, then `U(S)` is the schema definition bound to `X`

Unfolding reveals structure but does **not** recursively expand all references.

---

## 4. Simulation Functional

### 4.1 Simulation Relations

Let `R` be a binary relation over schemas.

Intuitively, `(A, B) ∈ R` means:
> whenever `A` accepts a value, `B` accepts it as well.

### 4.2 One-Step Simulation Functional

Define a monotone functional `F` over relations:

`(A, B) ∈ F(R)` iff:

1. The outer constructor of `A` is **compatible** with the outer constructor of `B`, and
2. For every place where `B` imposes a constraint, `A` imposes a compatible (stronger or equal) constraint, and
3. Whenever comparison recurses to subschemas, the resulting schema pairs are related by `R`.

Examples:
* Objects: properties in `B` must exist in `A` with compatible schemas
* Arrays: `items_A <| items_B`
* `oneOf`: each branch of `A` must simulate some branch of `B`
* Conditionals: all possible runtime paths must simulate

This definition is purely structural and syntax-directed.

---

## 5. Coinductive Definition of Subsumption

### 5.1 Greatest Fixpoint

Define subsumption as the **greatest fixpoint** of `F`:

    A <| B   ⇔   (A, B) ∈ νR. F(R)

This is a standard coinductive simulation definition.

### 5.2 Consequences

* Recursive schemas are handled naturally
* No unfolding depth is chosen a priori
* Cycles are allowed and expected

---

## 6. Unfolding Preserves Subsumption

### 6.1 Key Lemma (Unfold Congruence)

**Lemma.**
If `A <| B`, then:

    U(A) <| U(B)

### 6.2 Proof Sketch

* Since `<|` is defined as `νF`, it is a post-fixpoint:

      νF ⊆ F(νF)

* If `(A, B) ∈ F(νF)`, then unfolding both sides preserves outer compatibility
* Recursive comparisons still lie in `νF`
* Therefore `(U(A), U(B)) ∈ νF`

This proof is entirely semantic and does **not** depend on termination or finiteness.

---

## 7. Productivity and Algorithms

### 7.1 Semantic vs Algorithmic Concerns

The definition of `<|` is always meaningful.

However, **algorithms** that decide or approximate `<|` require termination guarantees.

### 7.2 Productivity Condition

A schema system is **productive** if:

> Along every `$ref` cycle, unfolding eventually exposes a structural constructor
> that introduces new observable constraints.

Non-productive examples:
* Pure `$ref` cycles with no structure
* Infinite alias chains

### 7.3 Finite Witness Property

Under productivity:

* If `A <| B` fails, there exists a **finite unfolding depth** at which the failure is observable
* SMT- and SAT-based procedures may safely search by increasing depth

---

## 8. SMT Interpretation

### 8.1 Predicate Encoding

Each schema `S` is encoded as a predicate `S(x)`.

Subsumption becomes:

    ∀x. A(x) ⇒ B(x)

### 8.2 Unfolding as Expansion

Unfolding corresponds to definitional expansion of predicates.

The unfold-congruence lemma guarantees soundness of expanding both sides.

---

## 9. Summary of Principles

1. Subsumption is a **coinductive simulation**
2. `$ref` is handled by coinduction, not by depth bounds
3. Unfolding preserves subsumption
4. Productivity is required only for **decision procedures**, not for meaning
5. Finite counterexamples exist under productivity

---

## 10. Design Implications

* Avoid definitions based on “there exists an unfolding depth”
* Treat unfolding as a congruence
* Separate semantic correctness from solver heuristics
* Use productivity only to justify termination strategies

---

This framework provides a minimal, correct, and implementation-aligned foundation
for recursive JSON Schema subsumption.
