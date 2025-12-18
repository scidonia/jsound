# JSSound Real-World Examples

This directory contains realistic JSON schema examples that demonstrate various schema evolution patterns and compatibility scenarios. JSSound now includes **enhanced explanations** that provide detailed insight into why schemas are incompatible and actionable recommendations for fixing them.

## API Evolution Examples

### User API Evolution (Compatible)
- **api_user_v1.json**: Strict v1 user schema with additionalProperties: false
- **api_user_v2_compatible.json**: v2 schema that allows additional properties

**Test:** `jsound api_user_v1.json api_user_v2_compatible.json`
**Result:** ✅ Compatible - v1 producers work with v2 consumers
**Pattern:** Adding optional fields while removing additionalProperties restriction

### E-commerce Product Evolution (Compatible)
- **ecommerce_product_v1.json**: v1 with limited currency enum and strict properties  
- **ecommerce_product_v2_expanded.json**: v2 with expanded currency options and flexible properties

**Test:** `jsound ecommerce_product_v1.json ecommerce_product_v2_expanded.json`
**Result:** ✅ Compatible - v1's enum subset works with v2's expanded enum, strict properties compatible with flexible
**Pattern:** Shows successful backward-compatible API evolution: enum expansion + removing property restrictions

### E-commerce Product Breaking Changes (Incompatible)
- **ecommerce_product_v1.json**: v1 with lenient constraints
- **ecommerce_product_v2_breaking.json**: v2 with stricter constraints and new required fields

**Test:** `jsound ecommerce_product_v1.json ecommerce_product_v2_breaking.json`
**Result:** ❌ Incompatible - Multiple breaking changes
**Enhanced Explanation:** JSSound identifies specific constraint violations:
- Required property `sku` missing from producer
- String length constraints tightened (`name` minLength: 1→10, maxLength: 200→50)
- Enum values restricted (`currency` supports EUR/GBP, consumer only accepts USD)
- Category constraint added (producer allows any string, consumer requires specific values)

### User Profile with Tags (Incompatible Arrays)
- **user_with_tags_v1.json**: User profile with flexible tag array
- **user_with_tags_v2_incompatible.json**: v2 with stricter array and format constraints

**Test:** `jsound user_with_tags_v1.json user_with_tags_v2_incompatible.json`
**Result:** ❌ Incompatible - Array and format constraint violations
**Enhanced Explanation:**
```
Counterexample: {'email': '4@d0H', 'tags': ['E'], 'username': 'CCB'}
Explanation: Missing required property 'id' | Missing required property 'preferences' | Property 'email' format mismatch: producer has 'email', consumer requires 'uri'
Failed constraints: ['required:id', 'required:preferences', 'format:email:email→uri']
Recommendations: ["Add 'id' to producer's required properties", "Add 'preferences' to producer's required properties", "Change producer property 'email' format from 'email' to 'uri'"]
```
**Pattern:** Demonstrates multiple constraint types: format mismatches, required properties, array constraints with `contains`

## Configuration Schema Examples

### Database Configuration
- **config_database_v1.json**: Basic database connection configuration

**Pattern:** Demonstrates required field validation and port number constraints

## API Response Examples

### REST API Response
- **rest_api_response_v1.json**: Generic API response with flexible data field

**Pattern:** Shows use of anyOf for flexible response data types

## Format Validation Examples

### Format Validation Schemas
- **format_validation_producer.json**: Schema with email, URI, date-time, and date formats
- **format_consumer_lenient.json**: Same structure but no format constraints (just strings)
- **format_email_only.json**: Schema requiring email format
- **format_different.json**: Schema requiring URI format  
- **format_custom.json**: Schema with custom/unknown format

**Test:** `jsound format_validation_producer.json format_consumer_lenient.json`
**Result:** ✅ Compatible - specific formats subsume general strings
**Pattern:** Format validation subsumption (strict ⊆ lenient)

**Test:** `jsound format_email_only.json format_different.json`
**Result:** ❌ Incompatible - different formats are incompatible
**Pattern:** Different format constraints are mutually exclusive

## Usage Examples

```bash
# Test compatible evolution
jsound examples/api_user_v1.json examples/api_user_v2_compatible.json
# Result: ✅ Compatible

# Test breaking changes with enhanced explanations
jsound examples/ecommerce_product_v1.json examples/ecommerce_product_v2_breaking.json
# Result: ❌ Incompatible with detailed explanation of constraint violations

# Test array constraint failures with explanations
jsound examples/user_with_tags_v1.json examples/user_with_tags_v2_incompatible.json
# Result: ❌ Incompatible with counterexample and specific failed constraints

# Test format validation compatibility
jsound examples/format_validation_producer.json examples/format_consumer_lenient.json
# Result: ✅ Compatible (specific formats subsume general strings)

# Test format incompatibility with explanations
jsound examples/format_email_only.json examples/format_different.json
# Result: ❌ Incompatible with format mismatch explanation

# Use enhanced API programmatically for detailed explanations
python -c "
from src.jsound.api import JSoundAPI
import json

with open('examples/user_with_tags_v1.json') as f:
    producer = json.load(f)
with open('examples/user_with_tags_v2_incompatible.json') as f:
    consumer = json.load(f)

api = JSoundAPI(explanations=True)  # Enable enhanced explanations
result = api.check_subsumption(producer, consumer)

if not result.is_compatible:
    print(f'Counterexample: {result.counterexample}')
    print(f'Explanation: {result.explanation}')
    print(f'Failed constraints: {result.failed_constraints}')
    print(f'Recommendations: {result.recommendations}')
"
```

## Schema Evolution Patterns Demonstrated

1. **Backward Compatible Evolution**: Adding optional fields and expanding enums
2. **Property Flexibility**: Removing additionalProperties restrictions maintains compatibility
3. **Breaking Changes with Enhanced Explanations**: 
   - Required property additions (`sku` field requirement)
   - Constraint tightening (string length, enum restrictions)
   - Format constraint mismatches (email vs URI)
4. **Array Constraint Evolution**:
   - Array length restrictions (`minItems`, `maxItems`)
   - Item constraint changes (`minLength` on array items)
   - Array `contains` constraint additions
5. **Format Validation**: Email, URI, date, date-time format constraints and subsumption
6. **Format Incompatibility**: Different format constraints are mutually exclusive
7. **Configuration Validation**: Required fields with type and range constraints
8. **API Response Flexibility**: Using anyOf for multiple data types
9. **Conditional Logic**: if/then/else constraints for conditional validation

## Enhanced Explanation Features

JSSound now provides **comprehensive explanations** for schema incompatibilities:

- **Meaningful Counterexamples**: Real JSON that demonstrates the incompatibility
- **Constraint Identification**: Specific failed constraints clearly labeled
- **Actionable Recommendations**: Concrete steps to fix compatibility issues
- **Pattern Recognition**: Automatic detection of common failure patterns
- **Multi-constraint Analysis**: Handles complex schemas with multiple simultaneous failures

These examples help understand when schema changes maintain compatibility, when they introduce breaking changes, and **exactly why and how to fix incompatibilities**.
