# jSound Real-World Examples

This directory contains realistic JSON schema examples that demonstrate various schema evolution patterns and compatibility scenarios. jSound now includes **enhanced explanations** that provide detailed insight into why schemas are incompatible and actionable recommendations for fixing them.

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
**Enhanced Explanation:** jSound identifies specific constraint violations:
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

### Database Configuration with Dependencies (Incompatible)
- **config_database_v1.json**: Basic database config without security dependencies
- **config_database_v2_secure.json**: v2 with strict security dependencies

**Test:** `jsound config_database_v1.json config_database_v2_secure.json`
**Result:** ❌ Incompatible - Dependency violations
**Enhanced Explanation:**
```
Counterexample: {'database_type': 'mysql', 'ssl_enabled': False}
Explanation: Property 'ssl_enabled' requires 'ssl_cert_path' but they are missing
Failed constraints: ['dependencies:ssl_enabled→ssl_cert_path']
Recommendations: ["Add properties 'ssl_cert_path' to producer schema when 'ssl_enabled' is present"]
```
**Pattern:** Demonstrates legacy `dependencies` feature - when SSL is enabled, certificate path becomes required

## API Response Examples

### REST API Response
- **rest_api_response_v1.json**: Generic API response with flexible data field

**Pattern:** Shows use of anyOf for flexible response data types

### API Configuration with Dependencies (Incompatible)
- **api_config_v1.json**: Basic API config without authentication dependencies
- **api_config_v2_incompatible.json**: v2 with strict authentication dependencies

**Test:** `jsound api_config_v1.json api_config_v2_incompatible.json`
**Result:** ❌ Incompatible - Complex dependency schema violations
**Pattern:** Demonstrates `dependentSchemas` with conditional authentication requirements (basic auth → username/password, bearer → token, etc.)

## Payment Form Examples

### Payment Form with Dependencies (Incompatible)
- **payment_form_v1.json**: Basic payment form without billing dependencies
- **payment_form_v2_strict.json**: v2 with strict billing and email dependencies

**Test:** `jsound payment_form_v1.json payment_form_v2_strict.json`
**Result:** ❌ Incompatible - Multiple dependency violations
**Enhanced Explanation:**
```
Counterexample: {'payment_method': 'credit_card'}
Explanation: Property 'payment_method' requires 'email' but they are missing
Failed constraints: ['dependentRequired:payment_method→email']
Recommendations: ["Add properties 'email' to producer schema when 'payment_method' is present"]
```
**Pattern:** Demonstrates `dependentRequired` - when credit card info is provided, billing address becomes required

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

# Test payment form dependencies with explanations
jsound examples/payment_form_v1.json examples/payment_form_v2_strict.json
# Result: ❌ Incompatible with dependency violation explanation

# Test database security dependencies
jsound examples/config_database_v1.json examples/config_database_v2_secure.json
# Result: ❌ Incompatible with security dependency violations

# Test API authentication dependencies
jsound examples/api_config_v1.json examples/api_config_v2_incompatible.json
# Result: ❌ Incompatible with authentication dependency violations

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
10. **Property Dependencies (`dependentRequired`)**: When one property exists, others become required
11. **Schema Dependencies (`dependentSchemas`)**: When one property exists, object must satisfy additional schema
12. **Legacy Dependencies**: Draft 7 `dependencies` supporting both property lists and schema objects
13. **Authentication Dependencies**: API configuration requiring appropriate credentials for each auth type
14. **Security Dependencies**: Database configuration requiring certificates when SSL is enabled
15. **Payment Dependencies**: Payment forms requiring billing info when payment methods are specified

## Enhanced Explanation Features

jSound now provides **comprehensive explanations** for schema incompatibilities:

- **Meaningful Counterexamples**: Real JSON that demonstrates the incompatibility
- **Constraint Identification**: Specific failed constraints clearly labeled
- **Actionable Recommendations**: Concrete steps to fix compatibility issues
- **Pattern Recognition**: Automatic detection of common failure patterns
- **Multi-constraint Analysis**: Handles complex schemas with multiple simultaneous failures

These examples help understand when schema changes maintain compatibility, when they introduce breaking changes, and **exactly why and how to fix incompatibilities**.
