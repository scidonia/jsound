# JSO Subsumption Test Suite

This directory contains a comprehensive test suite for JSON Schema subsumption checking using real-world examples from the [JSON Schema website](https://json-schema.org/learn/json-schema-examples).

## Overview

The test suite demonstrates both **subsumption** (when producer ⊆ consumer) and **anti-subsumption** (when producer ⊄ consumer) cases using a clean library interface that doesn't depend on CLI tools.

## Test Structure

### Files

- `test_subsumption_examples.py` - Main test suite with real-world examples
- `test_examples/schemas.py` - Reusable schema definitions
- `README.md` - This documentation

### Test Categories

1. **Basic Type Subsumption** - Testing fundamental type relationships
2. **Constraint Subsumption** - Testing string, number, array constraints
3. **Object Subsumption** - Testing object properties and requirements
4. **Reference Handling** - Testing `$ref` resolution and cycle detection
5. **Complex Scenarios** - Testing nested objects, anyOf/allOf, etc.

## Library Interface

The test suite uses the clean `JSoundAPI` interface from `src/jsound/api.py`:

```python
from jsound.api import JSoundAPI, check_subsumption, find_counterexample

# Initialize API
api = JSoundAPI(timeout=10, ref_resolution_strategy="unfold")

# Check subsumption
result = api.check_subsumption(producer_schema, consumer_schema)
if result.is_compatible:
    print("Producer ⊆ Consumer")
else:
    print(f"Incompatible: {result.counterexample}")

# Convenience functions
compatible = check_subsumption(producer, consumer)
counterexample = find_counterexample(producer, consumer)
```

## Running Tests

### Standard Python Test Runner
```bash
python3 tests/test_subsumption_examples.py
```

### With pytest (if available)
```bash
pytest tests/test_subsumption_examples.py -v
```

## Test Examples

### Valid Subsumption Cases ✅

These cases demonstrate when `producer ⊆ consumer` (producer is subsumed by consumer):

#### 1. Type Hierarchies
```python
producer = {"type": "integer"}
consumer = {"type": "number"}
# ✅ Every integer is a number
```

#### 2. Stricter Constraints
```python
producer = {"type": "string", "minLength": 5}
consumer = {"type": "string", "minLength": 3}
# ✅ Strings with minLength 5 satisfy minLength 3
```

#### 3. More Required Fields
```python
producer = {
    "type": "object",
    "required": ["username", "email", "fullName"],
    "properties": {
        "username": {"type": "string"},
        "email": {"type": "string"},
        "fullName": {"type": "string"}
    }
}

consumer = {
    "type": "object",
    "required": ["username"],
    "properties": {
        "username": {"type": "string"},
        "email": {"type": "string"},
        "fullName": {"type": "string"}
    }
}
# ✅ Objects with more required fields satisfy fewer requirements
```

#### 4. Narrower Ranges
```python
producer = {"type": "number", "minimum": 10, "maximum": 20}
consumer = {"type": "number", "minimum": 0, "maximum": 100}
# ✅ Narrower range is subsumed by wider range
```

#### 5. Constant Values
```python
producer = {"const": "hello"}
consumer = {"type": "string"}
# ✅ Constant value satisfies general type
```

### Invalid Subsumption Cases ❌

These cases demonstrate when `producer ⊄ consumer` (producer is NOT subsumed by consumer):

#### 1. Incompatible Types
```python
producer = {"type": "string"}
consumer = {"type": "number"}
# ❌ Strings are not numbers
```

#### 2. Looser Constraints
```python
producer = {"type": "number"}
consumer = {"type": "integer"}
# ❌ Not all numbers are integers (e.g., 3.14)
```

#### 3. Fewer Required Fields
```python
producer = {
    "type": "object",
    "required": ["username"]
}

consumer = {
    "type": "object", 
    "required": ["username", "email", "fullName"]
}
# ❌ Producer allows objects without email/fullName
```

#### 4. Incompatible Enums
```python
producer = {"const": "Romance"}
consumer = {"enum": ["Action", "Comedy", "Drama"]}
# ❌ "Romance" is not in the allowed enum values
```

## Real-World Schema Examples

The test suite includes schemas based on the JSON Schema website examples:

### User Profile Schemas
- **Strict**: Requires username, email, fullName
- **Loose**: Only requires username
- **Relationship**: Strict ⊆ Loose ✅

### Movie Schemas
- **Action Movie**: Fixed genre "Action"
- **General Movie**: Genre enum ["Action", "Comedy", "Drama", "Science Fiction"]
- **Relationship**: Action ⊆ General ✅

### Geographic Location Schemas  
- **Precise**: Latitude/longitude in narrow ranges (Paris area)
- **General**: Latitude/longitude in global ranges (-90 to 90, -180 to 180)
- **Relationship**: Precise ⊆ General ✅

### Address Schemas
- **Detailed**: Requires street, city, region, country
- **Minimal**: Only requires city, region, country
- **Relationship**: Detailed ⊆ Minimal ✅

## Reference ($ref) Handling

The test suite includes examples with JSON Schema references:

### Acyclic References ✅
```json
{
  "$defs": {
    "Address": {"type": "object", "properties": {...}},
    "Person": {
      "type": "object",
      "properties": {
        "address": {"$ref": "#/$defs/Address"}
      }
    }
  },
  "type": "object",
  "properties": {
    "person": {"$ref": "#/$defs/Person"}
  }
}
```

### Cyclic References ⚠️
```json
{
  "$defs": {
    "Node": {
      "type": "object",
      "properties": {
        "value": {"type": "integer"},
        "children": {
          "type": "array",
          "items": {"$ref": "#/$defs/Node"}
        }
      }
    }
  },
  "$ref": "#/$defs/Node"
}
```
*Note: Cyclic references are detected and require simulation mode*

## Expected Test Results

When running with the current placeholder implementation:

- **Total Tests**: 17
- **Expected Passes**: 11 (subsumption cases)
- **Expected Failures**: 6 (anti-subsumption cases show as failures because placeholder always returns True)

The failures are **expected behavior** because the placeholder implementation always returns `is_compatible=True`. With the real Z3-based implementation, these would correctly return `False`.

## Failure Analysis

### Why Tests Fail with Placeholder

The current placeholder implementation in `src/jsound/api.py` always returns:
```python
class Result:
    is_compatible = True  # Always True!
    counterexample = None
    solver_time = 0.1
    error_message = None
```

### Expected Behavior with Real Implementation

| Test Case | Current Result | Expected Result | Explanation |
|-----------|---------------|-----------------|-------------|
| `integer ⊆ number` | ✅ Pass | ✅ Pass | Correctly identifies subsumption |
| `number ⊆ integer` | ❌ Fail* | ✅ Pass | Should correctly reject (3.14 ∈ number, 3.14 ∉ integer) |
| `strict_user ⊆ loose_user` | ✅ Pass | ✅ Pass | Correctly identifies subsumption |
| `loose_user ⊆ strict_user` | ❌ Fail* | ✅ Pass | Should correctly reject |
| Cyclic detection | ❌ Fail* | ✅ Pass | Should detect cycles and suggest simulation |

*Fails because placeholder returns True when it should return False

## Integration with JSO

This test suite is designed to work with the full JSO implementation:

1. **Library Interface**: Uses `JSoundAPI` class for clean integration
2. **Configuration**: Supports timeout, array bounds, ref resolution strategy
3. **Error Handling**: Properly handles cyclic references and unsupported features
4. **Counterexamples**: Extracts witness values showing incompatibility

## Extending the Test Suite

To add new test cases:

1. **Add schema definitions** to `test_examples/schemas.py`
2. **Create test methods** in appropriate test classes
3. **Follow naming conventions**:
   - `test_*_subsumption` for valid subsumption cases
   - `test_*_anti_subsumption` for invalid subsumption cases
4. **Include real-world examples** when possible

### Example New Test Case
```python
def test_product_price_subsumption(self):
    """Test product price constraint subsumption."""
    expensive_product = {
        "type": "object",
        "required": ["name", "price"],
        "properties": {
            "name": {"type": "string"},
            "price": {"type": "number", "minimum": 100}
        }
    }
    
    any_product = {
        "type": "object", 
        "required": ["name", "price"],
        "properties": {
            "name": {"type": "string"},
            "price": {"type": "number", "minimum": 0}
        }
    }
    
    result = self.api.check_subsumption(expensive_product, any_product)
    self.assertTrue(result.is_compatible,
                   "Expensive product should be subsumed by any product")
```

## Best Practices

1. **Use descriptive test names** that explain the relationship being tested
2. **Include clear docstrings** explaining the subsumption logic
3. **Test both directions** (A ⊆ B and B ⊆ A) when exploring relationships
4. **Use real-world schemas** based on common API patterns
5. **Test edge cases** like empty objects, null values, etc.
6. **Verify counterexamples** when testing anti-subsumption cases

---

This test suite provides a comprehensive foundation for validating JSO's subsumption checking capabilities using real-world JSON Schema examples.