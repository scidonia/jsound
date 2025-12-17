# JSSound Real-World Examples

This directory contains realistic JSON schema examples that demonstrate various schema evolution patterns and compatibility scenarios.

## API Evolution Examples

### User API Evolution (Compatible)
- **api_user_v1.json**: Strict v1 user schema with additionalProperties: false
- **api_user_v2_compatible.json**: v2 schema that allows additional properties

**Test:** `jsound api_user_v1.json api_user_v2_compatible.json`
**Result:** ✅ Compatible - v1 producers work with v2 consumers
**Pattern:** Adding optional fields while removing additionalProperties restriction

### E-commerce Product Evolution (Incompatible)
- **ecommerce_product_v1.json**: v1 with limited currency enum and strict properties
- **ecommerce_product_v2_expanded.json**: v2 with expanded currency options and flexible properties

**Test:** `jsound ecommerce_product_v1.json ecommerce_product_v2_expanded.json`
**Result:** ❌ Incompatible - conflicting evolution (enum expansion vs strict properties)
**Pattern:** Shows how expanding enums while adding flexibility can break compatibility

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
jsound examples/api_user_v1.json examples/api_user_v2_compatible.json --show-verification

# Test incompatible evolution
jsound examples/ecommerce_product_v1.json examples/ecommerce_product_v2_expanded.json --verbose

# Test with detailed verification conditions
jsound examples/producer_loose.json examples/consumer_strict.json --show-verification

# Test format validation
jsound examples/format_validation_producer.json examples/format_consumer_lenient.json --verbose

# Test incompatible formats
jsound examples/format_email_only.json examples/format_different.json --verbose
```

## Schema Evolution Patterns Demonstrated

1. **Backward Compatible Evolution**: Adding optional fields
2. **Breaking Changes**: Expanding enums while restricting additional properties  
3. **API Response Flexibility**: Using anyOf for multiple data types
4. **Configuration Validation**: Required fields with type and range constraints
5. **Format Validation**: Email, URI, date, date-time format constraints and subsumption
6. **Conditional Logic**: if/then/else constraints for conditional validation

These examples help understand when schema changes maintain compatibility and when they introduce breaking changes.
