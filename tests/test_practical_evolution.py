"""
Practical Schema Evolution Tests: Real-world API evolution scenarios.

This test suite demonstrates practical evolution scenarios where APIs evolve
while maintaining backward compatibility with existing consumers. Based on
real-world JSON Schema examples from json-schema.org/learn/json-schema-examples

Evolution Principles Demonstrated:
1. ✅ Adding optional fields (backwards compatible)
2. ✅ Relaxing constraints (expanding valid values)
3. ✅ Making required fields optional (producer evolution)
4. ✅ Allowing additional properties (flexibility)
5. ❌ Breaking changes (incompatible evolution)

Test Philosophy: Producers should be able to evolve to provide more features
while existing consumers continue to work unchanged.
"""

import pytest


@pytest.mark.evolution
class TestAPIEvolution:
    """Test realistic API evolution scenarios."""

    def test_user_profile_api_v1_to_v2(self, api):
        """User profile API adds optional social media fields."""
        # API v1: Consumer expects basic user profile
        consumer_v1 = {
            "type": "object",
            "required": ["username", "email"],
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string"},
                "fullName": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": True,  # Consumer allows future extensions
        }

        # API v2: Producer adds social media integration (all optional)
        producer_v2 = {
            "type": "object",
            "required": ["username", "email"],
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string"},
                "fullName": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
                # v2 additions - all optional for backward compatibility
                "avatar": {"type": "string"},
                "bio": {"type": "string"},
                "location": {"type": "string"},
                "joinDate": {"type": "string", "format": "date"},
            },
            "additionalProperties": False,
        }

        result = api.check_subsumption(producer_v2, consumer_v1)
        assert result.is_compatible, (
            "Producer v2 with optional fields should be compatible with consumer v1"
        )

    def test_ecommerce_product_catalog_evolution(self, api):
        """E-commerce product catalog evolves to support new categories."""
        # Original: Basic product consumer
        basic_consumer = {
            "type": "object",
            "required": ["name", "price"],
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number", "minimum": 0},
                "category": {"type": "string"},  # Accept any category
                "inStock": {"type": "boolean"},
            },
            "additionalProperties": True,
        }

        # Evolution: Producer supports expanded categories and features
        enhanced_producer = {
            "type": "object",
            "required": ["name", "price"],  # Same core requirements
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number", "minimum": 0},
                "category": {
                    "type": "string",
                    "enum": [
                        "Electronics",
                        "Books",
                        "Clothing",
                        "Home",
                        "Sports",
                        "Toys",
                    ],  # Specific allowed categories
                },
                "inStock": {"type": "boolean"},
                "sku": {"type": "string"},
                "description": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        }

        # This should work: producer with specific categories ⊆ consumer accepting any category
        result = api.check_subsumption(enhanced_producer, basic_consumer)
        assert result.is_compatible, (
            "Enhanced producer with specific categories should work with flexible consumer"
        )

    def test_job_posting_platform_evolution(self, api):
        """Job posting platform evolves to support remote work."""
        # Consumer v1: Traditional job posting processor
        traditional_consumer = {
            "type": "object",
            "required": ["title", "company", "description"],
            "properties": {
                "title": {"type": "string"},
                "company": {"type": "string"},
                "location": {"type": "string"},  # Optional in consumer
                "description": {"type": "string"},
                "salary": {"type": "number", "minimum": 0},
                "employmentType": {"type": "string"},
            },
            "additionalProperties": True,
        }

        # Producer v2: Supports both traditional and remote positions
        modern_producer = {
            "type": "object",
            "required": ["title", "company", "description"],  # Core fields
            "properties": {
                "title": {"type": "string"},
                "company": {"type": "string"},
                "location": {"type": "string"},  # Optional (for remote jobs)
                "description": {"type": "string"},
                "salary": {"type": "number", "minimum": 0},
                "employmentType": {
                    "type": "string",
                    "enum": ["Full-time", "Part-time", "Contract", "Remote"],
                },
                "remoteWorkPolicy": {
                    "type": "string",
                    "enum": ["Office-only", "Hybrid", "Fully-remote"],
                },
            },
            "additionalProperties": False,
        }

        result = api.check_subsumption(modern_producer, traditional_consumer)
        assert result.is_compatible, (
            "Modern producer supporting remote work should be compatible with traditional consumer"
        )

    def test_health_record_privacy_evolution(self, api):
        """Healthcare API evolves to support privacy-focused patient records."""
        # Consumer: Healthcare system accepting patient data
        healthcare_consumer = {
            "type": "object",
            "required": ["patientId", "dateOfBirth"],  # Minimal required info
            "properties": {
                "patientId": {"type": "string"},
                "patientName": {"type": "string"},  # Optional for privacy
                "dateOfBirth": {"type": "string", "format": "date"},
                "bloodType": {"type": "string"},
                "allergies": {"type": "array", "items": {"type": "string"}},
                "conditions": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": True,
        }

        # Producer: Privacy-enhanced medical record system
        privacy_producer = {
            "type": "object",
            "required": ["patientId", "dateOfBirth"],
            "properties": {
                "patientId": {"type": "string"},
                "dateOfBirth": {"type": "string", "format": "date"},
                "bloodType": {
                    "type": "string",
                    "enum": [
                        "A+",
                        "A-",
                        "B+",
                        "B-",
                        "AB+",
                        "AB-",
                        "O+",
                        "O-",
                        "Unknown",
                    ],
                },
                "allergies": {"type": "array", "items": {"type": "string"}},
                "conditions": {"type": "array", "items": {"type": "string"}},
                "privacyLevel": {
                    "type": "string",
                    "enum": ["Public", "Restricted", "Confidential"],
                },
                "lastUpdated": {"type": "string", "format": "date-time"},
            },
            "additionalProperties": False,
        }

        result = api.check_subsumption(privacy_producer, healthcare_consumer)
        assert result.is_compatible, (
            "Privacy-enhanced producer should be compatible with healthcare consumer"
        )

    def test_breaking_change_detection(self, api):
        """Demonstrate detection of breaking changes in evolution."""
        # Consumer: Expects integer user IDs
        consumer_expecting_int_id = {
            "type": "object",
            "required": ["userId", "name"],
            "properties": {
                "userId": {"type": "integer"},  # Expects integer ID
                "name": {"type": "string"},
                "email": {"type": "string"},
            },
            "additionalProperties": True,
        }

        # Producer: Breaking change - switches to string UUIDs
        producer_with_uuid = {
            "type": "object",
            "required": ["userId", "name"],
            "properties": {
                "userId": {"type": "string"},  # BREAKING: Now string UUID
                "name": {"type": "string"},
                "email": {"type": "string"},
            },
            "additionalProperties": False,
        }

        result = api.check_subsumption(producer_with_uuid, consumer_expecting_int_id)
        assert not result.is_compatible, (
            "Producer changing data type should not be compatible (breaking change)"
        )
        assert result.counterexample is not None, (
            "Should provide counterexample showing the type conflict"
        )

    def test_enum_expansion_compatibility(self, api):
        """Test expanding enum values (should be compatible in correct direction)."""
        # Consumer: Accepts any status string
        flexible_consumer = {
            "type": "object",
            "properties": {
                "orderId": {"type": "string"},
                "status": {"type": "string"},  # Any string status
                "total": {"type": "number"},
            },
            "additionalProperties": True,
        }

        # Producer: Limited to specific statuses
        specific_producer = {
            "type": "object",
            "required": ["orderId", "status"],
            "properties": {
                "orderId": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": [
                        "pending",
                        "processing",
                        "shipped",
                        "delivered",
                        "cancelled",
                    ],
                },
                "total": {"type": "number", "minimum": 0},
            },
            "additionalProperties": False,
        }

        # Specific enum values ⊆ general string should work
        result = api.check_subsumption(specific_producer, flexible_consumer)
        assert result.is_compatible, (
            "Producer with specific enum values should be compatible with consumer accepting any string"
        )

    def test_required_field_relaxation(self, api):
        """Test making required fields optional (producer evolution)."""
        # Consumer: Flexible - only requires essential fields
        flexible_consumer = {
            "type": "object",
            "required": ["eventId", "title"],  # Minimal requirements
            "properties": {
                "eventId": {"type": "string"},
                "title": {"type": "string"},
                "date": {"type": "string", "format": "date"},
                "location": {"type": "string"},
                "capacity": {"type": "integer", "minimum": 1},
            },
            "additionalProperties": True,
        }

        # Producer: Strict - requires all event details
        strict_producer = {
            "type": "object",
            "required": ["eventId", "title", "date", "location"],  # More requirements
            "properties": {
                "eventId": {"type": "string"},
                "title": {"type": "string"},
                "date": {"type": "string", "format": "date"},
                "location": {"type": "string"},
                "capacity": {"type": "integer", "minimum": 1},
                "description": {"type": "string"},
            },
            "additionalProperties": False,
        }

        # Strict producer ⊆ flexible consumer should work
        result = api.check_subsumption(strict_producer, flexible_consumer)
        assert result.is_compatible, (
            "Strict producer with more required fields should be compatible with flexible consumer"
        )


@pytest.mark.evolution
class TestRealWorldEvolutionPatterns:
    """Test common real-world API evolution patterns."""

    def test_pagination_api_evolution(self, api):
        """API evolves from simple list to paginated response."""
        # Consumer v1: Expects simple array response
        simple_consumer = {
            "type": "object",
            "required": ["items"],
            "properties": {
                "items": {"type": "array", "items": {"type": "object"}},
            },
            "additionalProperties": True,  # Allow pagination metadata
        }

        # Producer v2: Adds pagination metadata
        paginated_producer = {
            "type": "object",
            "required": ["items"],  # Still provides required items
            "properties": {
                "items": {"type": "array", "items": {"type": "object"}},
                "pagination": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer", "minimum": 1},
                        "pageSize": {"type": "integer", "minimum": 1},
                        "totalItems": {"type": "integer", "minimum": 0},
                        "totalPages": {"type": "integer", "minimum": 0},
                    },
                },
            },
            "additionalProperties": False,
        }

        result = api.check_subsumption(paginated_producer, simple_consumer)
        assert result.is_compatible, (
            "Paginated producer should be backward compatible with simple consumer"
        )

    def test_error_response_standardization(self, api):
        """Error response format evolves to include more debugging info."""
        # Consumer: Basic error handler
        basic_error_consumer = {
            "type": "object",
            "required": ["error"],
            "properties": {
                "error": {"type": "string"},
                "code": {"type": "integer"},
            },
            "additionalProperties": True,
        }

        # Producer: Enhanced error details
        detailed_error_producer = {
            "type": "object",
            "required": ["error"],
            "properties": {
                "error": {"type": "string"},
                "code": {"type": "integer"},
                "details": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "reason": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"},
                    },
                },
                "requestId": {"type": "string"},
            },
            "additionalProperties": False,
        }

        result = api.check_subsumption(detailed_error_producer, basic_error_consumer)
        assert result.is_compatible, (
            "Enhanced error producer should be compatible with basic error consumer"
        )


if __name__ == "__main__":
    print("=" * 70)
    print("Practical Schema Evolution Tests")
    print("Testing real-world API evolution compatibility patterns")
    print("=" * 70)
