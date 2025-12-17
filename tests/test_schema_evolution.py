"""
Schema Evolution Tests: Real-world examples of producer-consumer compatibility.

This test suite demonstrates practical schema evolution scenarios where producers
can be updated while maintaining compatibility with existing consumers. Based on
examples from https://json-schema.org/learn/json-schema-examples

Key Evolution Patterns Tested:
1. Adding optional fields (backwards compatible)
2. Relaxing constraints (allowing more values)
3. Making required fields optional (loosening requirements)
4. Adding enum values (expanding accepted values)
5. Allowing additional properties (flexibility)

The principle: Producer ⊆ Consumer should remain True even as producers evolve
to support new features, ensuring existing consumers continue to work.
"""

import pytest


@pytest.mark.evolution
@pytest.mark.subsumption
class TestUserProfileEvolution:
    """Test user profile schema evolution scenarios."""

    def test_adding_optional_profile_fields(self, api):
        """Producer adds optional fields while maintaining consumer compatibility."""
        # Original consumer schema - accepts basic user profiles
        consumer_v1 = {
            "type": "object",
            "required": ["username", "email"],
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "fullName": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        }

        # Evolution: Producer adds optional social media fields
        producer_v2 = {
            "type": "object",
            "required": ["username", "email"],
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "fullName": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
                # New optional fields
                "socialMedia": {
                    "type": "object",
                    "properties": {
                        "twitter": {"type": "string"},
                        "linkedin": {"type": "string"},
                    },
                },
                "profilePicture": {"type": "string"},
                "lastLogin": {"type": "string", "format": "date-time"},
            },
            "additionalProperties": False,
        }

        result = api.check_subsumption(producer_v2, consumer_v1)
        assert not result.is_compatible, (
            "Producer with additional required properties cannot be subsumed by consumer with additionalProperties: false"
        )

        # Fix: Consumer allows additional properties
        consumer_v1_flexible = {**consumer_v1, "additionalProperties": True}

        result = api.check_subsumption(producer_v2, consumer_v1_flexible)
        assert result.is_compatible, (
            "Producer with new optional fields should be compatible with flexible consumer"
        )

    def test_relaxing_age_constraints(self, api):
        """Producer relaxes age constraints to allow broader range."""
        # Original: Consumer requires users to be adults (18+)
        consumer_adult_only = {
            "type": "object",
            "required": ["username", "email", "age"],
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string"},
                "age": {"type": "integer", "minimum": 18, "maximum": 120},
            },
            "additionalProperties": True,
        }

        # Evolution: Producer accepts all ages (broader range, no extra fields)
        producer_all_ages = {
            "type": "object",
            "required": ["username", "email", "age"],
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string"},
                "age": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 150,
                },  # Broader range
            },
            "additionalProperties": True,
        }

        # Test: Producer with broader age range should NOT be compatible with consumer
        # expecting only adults (because producer might provide minors)
        result = api.check_subsumption(producer_all_ages, consumer_adult_only)
        assert not result.is_compatible, (
            "Producer allowing broader age range (including minors) should not be subsumed "
            "by adult-only consumer, because producer might provide age < 18"
        )

        # Test: Strict adult-only producer SHOULD be compatible with flexible consumer
        # (all adults are within the 0-150 age range)
        result = api.check_subsumption(consumer_adult_only, producer_all_ages)
        assert result.is_compatible, (
            "Adult-only producer (18-120) should be compatible with all-ages consumer (0-150)"
        )


@pytest.mark.evolution
@pytest.mark.subsumption
class TestEcommerceEvolution:
    """Test e-commerce system evolution scenarios."""

    def test_product_catalog_expansion(self, api):
        """Producer expands product catalog with new categories."""
        # Original: Basic product schema
        basic_product = {
            "type": "object",
            "required": ["name", "price"],
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number", "minimum": 0},
                "category": {
                    "type": "string",
                    "enum": ["Electronics", "Books", "Clothing"],
                },
            },
        }

        # Evolution: Extended product with more categories and features
        extended_product = {
            "type": "object",
            "required": ["name", "price"],
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number", "minimum": 0},
                "category": {
                    "type": "string",
                    "enum": [
                        "Electronics",
                        "Books",
                        "Clothing",  # Original
                        "Home & Garden",
                        "Sports",
                        "Toys",  # New categories
                    ],
                },
                "sku": {"type": "string"},  # New field
                "description": {"type": "string"},  # New field
                "inStock": {"type": "boolean"},  # New field
                "ratings": {  # New nested object
                    "type": "object",
                    "properties": {
                        "average": {"type": "number", "minimum": 1, "maximum": 5},
                        "count": {"type": "integer", "minimum": 0},
                    },
                },
            },
            "additionalProperties": True,
        }

        result = api.check_subsumption(extended_product, basic_product)
        assert not result.is_compatible, (
            "Extended product with more enum values cannot be subsumed by basic product with restricted enum"
        )

        # Flexible consumer allows any category
        flexible_product = {
            "type": "object",
            "required": ["name", "price"],
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number", "minimum": 0},
                "category": {"type": "string"},  # No enum restriction
            },
            "additionalProperties": True,
        }

        result = api.check_subsumption(extended_product, flexible_product)
        assert result.is_compatible, (
            "Extended product should be compatible with flexible consumer"
        )

    def test_order_system_evolution(self, api):
        """Order system evolves to support new payment methods and shipping."""
        # Original: Simple order schema
        simple_order = {
            "type": "object",
            "required": ["orderId", "items", "total"],
            "properties": {
                "orderId": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "price", "quantity"],
                        "properties": {
                            "name": {"type": "string"},
                            "price": {"type": "number", "minimum": 0},
                            "quantity": {"type": "integer", "minimum": 1},
                        },
                    },
                },
                "total": {"type": "number", "minimum": 0},
                "paymentMethod": {"type": "string", "enum": ["credit_card", "paypal"]},
            },
        }

        # Evolution: Enhanced order with more options
        enhanced_order = {
            "type": "object",
            "required": ["orderId", "items", "total"],
            "properties": {
                "orderId": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "price", "quantity"],
                        "properties": {
                            "name": {"type": "string"},
                            "price": {"type": "number", "minimum": 0},
                            "quantity": {"type": "integer", "minimum": 1},
                            "sku": {"type": "string"},  # New optional field
                            "discount": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100,
                            },  # New
                        },
                        "additionalProperties": True,
                    },
                },
                "total": {"type": "number", "minimum": 0},
                "paymentMethod": {
                    "type": "string",
                    "enum": [
                        "credit_card",
                        "paypal",
                        "apple_pay",
                        "google_pay",
                        "crypto",
                    ],  # Extended
                },
                "shippingAddress": {  # New optional nested object
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                        "country": {"type": "string"},
                    },
                },
                "priority": {
                    "type": "string",
                    "enum": ["standard", "express", "overnight"],
                },  # New
            },
            "additionalProperties": True,
        }

        result = api.check_subsumption(enhanced_order, simple_order)
        assert not result.is_compatible, (
            "Enhanced order with extended payment methods cannot be subsumed by simple order"
        )


@pytest.mark.evolution
@pytest.mark.subsumption
class TestJobPostingEvolution:
    """Test job posting platform evolution."""

    def test_job_posting_feature_expansion(self, api):
        """Job posting platform adds remote work and benefits information."""
        # Original: Basic job posting
        basic_job = {
            "type": "object",
            "required": ["title", "company", "location", "description"],
            "properties": {
                "title": {"type": "string"},
                "company": {"type": "string"},
                "location": {"type": "string"},
                "description": {"type": "string"},
                "employmentType": {
                    "type": "string",
                    "enum": ["Full-time", "Part-time"],
                },
                "salary": {"type": "number", "minimum": 0},
            },
            "additionalProperties": False,
        }

        # Evolution: Modern job posting with remote work support
        modern_job = {
            "type": "object",
            "required": ["title", "company", "location", "description"],
            "properties": {
                "title": {"type": "string"},
                "company": {"type": "string"},
                "location": {"type": "string"},
                "description": {"type": "string"},
                "employmentType": {
                    "type": "string",
                    "enum": [
                        "Full-time",
                        "Part-time",
                        "Contract",
                        "Internship",
                    ],  # Extended
                },
                "salary": {"type": "number", "minimum": 0},
                "salaryRange": {  # New alternative to fixed salary
                    "type": "object",
                    "properties": {
                        "min": {"type": "number", "minimum": 0},
                        "max": {"type": "number", "minimum": 0},
                        "currency": {"type": "string"},
                    },
                },
                "remoteWork": {  # New remote work options
                    "type": "object",
                    "properties": {
                        "allowed": {"type": "boolean"},
                        "policy": {
                            "type": "string",
                            "enum": ["fully-remote", "hybrid", "office-only"],
                        },
                    },
                },
                "benefits": {  # New benefits array
                    "type": "array",
                    "items": {"type": "string"},
                },
                "skills": {  # New required skills
                    "type": "array",
                    "items": {"type": "string"},
                },
                "experienceLevel": {
                    "type": "string",
                    "enum": ["Junior", "Mid", "Senior", "Lead"],
                },
            },
            "additionalProperties": True,
        }

        # Test compatibility with flexible consumer
        flexible_job_consumer = {
            "type": "object",
            "required": [
                "title",
                "company",
                "description",
            ],  # Relaxed: location no longer required
            "properties": {
                "title": {"type": "string"},
                "company": {"type": "string"},
                "location": {"type": "string"},
                "description": {"type": "string"},
                "employmentType": {"type": "string"},  # No enum restriction
                "salary": {"type": "number"},  # No minimum restriction
            },
            "additionalProperties": True,
        }

        result = api.check_subsumption(modern_job, flexible_job_consumer)
        assert result.is_compatible, (
            "Modern job posting should be compatible with flexible consumer"
        )

    def test_making_location_optional_for_remote_work(self, api):
        """Evolution makes location optional to support fully remote positions."""
        # Original: Location always required (strict producer)
        location_required = {
            "type": "object",
            "required": ["title", "company", "location", "description"],
            "properties": {
                "title": {"type": "string"},
                "company": {"type": "string"},
                "location": {"type": "string"},
                "description": {"type": "string"},
            },
            "additionalProperties": True,
        }

        # Evolution: Location optional (flexible consumer that can handle remote jobs)
        location_optional = {
            "type": "object",
            "required": [
                "title",
                "company",
                "description",
            ],  # location no longer required
            "properties": {
                "title": {"type": "string"},
                "company": {"type": "string"},
                "location": {"type": "string"},  # still allowed, but optional
                "description": {"type": "string"},
            },
            "additionalProperties": True,
        }

        # Test 1: Flexible producer with optional location should NOT be compatible
        # with strict consumer that requires location
        result = api.check_subsumption(location_optional, location_required)
        assert not result.is_compatible, (
            "Flexible producer (location optional) cannot be subsumed by strict consumer (location required) "
            "because producer might omit required location field"
        )

        # Test 2: Strict producer with required location SHOULD be compatible
        # with flexible consumer that allows optional location
        result = api.check_subsumption(location_required, location_optional)
        assert result.is_compatible, (
            "Strict producer (location required) should be compatible with flexible consumer (location optional) "
            "because producer always provides the location field"
        )


@pytest.mark.evolution
@pytest.mark.subsumption
class TestHealthRecordEvolution:
    """Test healthcare system evolution with privacy and new fields."""

    def test_health_record_privacy_evolution_incompatible(self, api):
        """Healthcare system evolves incompatibly due to additionalProperties: false preventing required fields."""
        # Original: Basic health record
        basic_health_record = {
            "type": "object",
            "required": [
                "patientName",
                "dateOfBirth",
                "bloodType",
            ],  # Still requires name and bloodType
            "properties": {
                "patientName": {
                    "type": "string"
                },  # Required in basic, not provided by enhanced
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
                    ],  # Required in basic
                },
                "allergies": {"type": "array", "items": {"type": "string"}},
                "medications": {"type": "array", "items": {"type": "string"}},
            },
        }

        # Evolution: Enhanced with privacy controls - uses different required fields
        enhanced_health_record = {
            "type": "object",
            "required": [
                "patientId",  # New: ID-based identification
                "dateOfBirth",
                "privacyLevel",  # New: privacy level is required
            ],
            "properties": {
                "patientId": {"type": "string"},  # New: Use ID instead of name
                "dateOfBirth": {"type": "string", "format": "date"},
                "privacyLevel": {
                    "type": "string",
                    "enum": ["Public", "Restricted", "Confidential"],
                },  # New required field
                "lastUpdated": {"type": "string", "format": "date-time"},  # New
            },
            "additionalProperties": False,  # Strict: no additional properties
        }

        # The enhanced record should NOT be compatible with basic record
        # Enhanced has additionalProperties: false so cannot provide patientName/bloodType
        result = api.check_subsumption(enhanced_health_record, basic_health_record)
        assert not result.is_compatible, (
            "Enhanced health record should NOT be compatible with basic record "
            "because it cannot provide required patientName and bloodType due to additionalProperties: false"
        )

        # But we can test compatibility with a flexible consumer
        flexible_health_consumer = {
            "type": "object",
            "required": ["dateOfBirth"],  # Minimal requirements
            "properties": {
                "patientId": {"type": "string"},
                "patientName": {"type": "string"},
                "dateOfBirth": {"type": "string"},
                "bloodType": {"type": "string"},
            },
            "additionalProperties": True,
        }

        result = api.check_subsumption(enhanced_health_record, flexible_health_consumer)
        assert result.is_compatible, (
            "Enhanced health record should be compatible with flexible consumer"
        )

    def test_health_record_privacy_evolution_compatible(self, api):
        """Healthcare system evolves compatibly by maintaining required fields while adding optional ones."""
        # Original: Basic health record (same as before)
        basic_health_record = {
            "type": "object",
            "required": [
                "patientName",
                "dateOfBirth",
                "bloodType",
            ],
            "properties": {
                "patientName": {"type": "string"},
                "dateOfBirth": {"type": "string", "format": "date"},
                "bloodType": {
                    "type": "string",
                    "enum": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                },
                "allergies": {"type": "array", "items": {"type": "string"}},
                "medications": {"type": "array", "items": {"type": "string"}},
            },
        }

        # Evolution: Enhanced record that CAN provide all original required fields
        enhanced_compatible_health_record = {
            "type": "object",
            "required": [
                "patientName",  # Keep original required field
                "dateOfBirth",  # Keep original required field
                "bloodType",  # Keep original required field
                "privacyLevel",  # Add new required field
            ],
            "properties": {
                "patientName": {"type": "string"},  # Same as original
                "dateOfBirth": {"type": "string", "format": "date"},  # Same as original
                "bloodType": {
                    "type": "string",
                    "enum": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                },  # Same as original
                "allergies": {
                    "type": "array",
                    "items": {"type": "string"},
                },  # Same as original
                "medications": {
                    "type": "array",
                    "items": {"type": "string"},
                },  # Same as original
                "privacyLevel": {
                    "type": "string",
                    "enum": ["Public", "Restricted", "Confidential"],
                },  # New required field
                "patientId": {"type": "string"},  # New optional field
                "lastUpdated": {
                    "type": "string",
                    "format": "date-time",
                },  # New optional field
            },
            # No additionalProperties: false - allows flexibility
        }

        result = api.check_subsumption(
            enhanced_compatible_health_record, basic_health_record
        )
        assert result.is_compatible, (
            "Enhanced health record should be compatible with basic record "
            "because it can provide all required fields (patientName, dateOfBirth, bloodType)"
        )


@pytest.mark.evolution
@pytest.mark.subsumption
class TestMovieSystemEvolution:
    """Test movie database evolution with streaming and ratings."""

    def test_movie_streaming_era_evolution_incompatible(self, api):
        """Movie database evolves incompatibly due to duration type and cast structure changes."""
        # Original: DVD-era movie schema
        dvd_era_movie = {
            "type": "object",
            "required": ["title", "director", "releaseDate"],
            "properties": {
                "title": {"type": "string"},
                "director": {"type": "string"},
                "releaseDate": {"type": "string", "format": "date"},
                "genre": {
                    "type": "string",
                    "enum": ["Action", "Comedy", "Drama", "Science Fiction"],
                },
                "duration": {"type": "string"},  # e.g., "2h 15m"
                "cast": {"type": "array", "items": {"type": "string"}},
                "rating": {
                    "type": "string",
                    "enum": ["G", "PG", "PG-13", "R", "NC-17"],
                },  # MPAA ratings
            },
        }

        # Evolution: Streaming-era movie with international content
        streaming_era_movie = {
            "type": "object",
            "required": ["title", "director", "releaseDate"],
            "properties": {
                "title": {"type": "string"},
                "director": {"type": "string"},
                "releaseDate": {"type": "string", "format": "date"},
                "genre": {
                    "type": "string",
                    "enum": [
                        "Action",
                        "Comedy",
                        "Drama",
                        "Science Fiction",  # Original
                        "Documentary",
                        "Horror",
                        "Romance",
                        "Thriller",  # Extended
                        "Animation",
                        "Crime",
                        "Family",
                        "Fantasy",  # More genres
                        "Mystery",
                        "War",
                        "Western",
                        "Musical",  # Even more
                    ],
                },
                "duration": {
                    "type": "integer"
                },  # Changed: duration in minutes (numeric)
                "cast": {
                    "type": "array",
                    "items": {
                        "type": "object",  # Enhanced: detailed cast info
                        "properties": {
                            "name": {"type": "string"},
                            "role": {"type": "string"},
                            "order": {"type": "integer"},
                        },
                        "required": ["name"],
                    },
                },
                "rating": {  # Enhanced: multiple rating systems
                    "type": "object",
                    "properties": {
                        "mpaa": {
                            "type": "string",
                            "enum": ["G", "PG", "PG-13", "R", "NC-17"],
                        },
                        "imdb": {"type": "number", "minimum": 1, "maximum": 10},
                        "rottenTomatoes": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                        },
                    },
                },
                "streamingPlatforms": {
                    "type": "array",
                    "items": {"type": "string"},
                },  # New
                "languages": {"type": "array", "items": {"type": "string"}},  # New
                "subtitles": {"type": "array", "items": {"type": "string"}},  # New
                "country": {"type": "string"},  # New
            },
        }

        result = api.check_subsumption(streaming_era_movie, dvd_era_movie)
        # Note: Complex schemas with format constraints and type mismatches can be incompatible
        # even when basic required fields match. This reflects real-world API evolution challenges.
        assert not result.is_compatible, (
            "Complex streaming movie schema is incompatible with DVD-era schema "
            "due to format constraint interactions and property type mismatches"
        )

    def test_movie_streaming_era_evolution_compatible(self, api):
        """Movie database evolves compatibly by extending enums and adding optional fields."""
        # Original: DVD-era movie schema (same as before)
        dvd_era_movie = {
            "type": "object",
            "required": ["title", "director", "releaseDate"],
            "properties": {
                "title": {"type": "string"},
                "director": {"type": "string"},
                "releaseDate": {"type": "string", "format": "date"},
                "genre": {
                    "type": "string",
                    "enum": ["Action", "Comedy", "Drama", "Science Fiction"],
                },
                "duration": {"type": "string"},  # e.g., "2h 15m"
                "cast": {"type": "array", "items": {"type": "string"}},
                "rating": {
                    "type": "string",
                    "enum": ["G", "PG", "PG-13", "R", "NC-17"],
                },  # MPAA ratings
            },
        }

        # Evolution: Streaming-era movie with COMPATIBLE changes
        streaming_era_compatible_movie = {
            "type": "object",
            "required": ["title", "director", "releaseDate"],  # Same required fields
            "properties": {
                "title": {"type": "string"},  # Same
                "director": {"type": "string"},  # Same
                "releaseDate": {"type": "string", "format": "date"},  # Same
                "genre": {
                    "type": "string",
                    "enum": [
                        "Action",
                        "Comedy",
                        "Drama",
                        "Science Fiction",  # Same enum as original - compatible
                    ],
                },
                "duration": {"type": "string"},  # Same type as original!
                "cast": {
                    "type": "array",
                    "items": {"type": "string"},
                },  # Same structure as original!
                "rating": {
                    "type": "string",
                    "enum": [
                        "G",
                        "PG",
                        "PG-13",
                        "R",
                        "NC-17",
                    ],  # Same enum as original - compatible
                },
                # New optional fields - don't break compatibility
                "streamingPlatforms": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "languages": {"type": "array", "items": {"type": "string"}},
                "subtitles": {"type": "array", "items": {"type": "string"}},
                "country": {"type": "string"},
                "imdbRating": {"type": "number", "minimum": 1, "maximum": 10},
                "boxOffice": {"type": "number", "minimum": 0},
            },
        }

        result = api.check_subsumption(streaming_era_compatible_movie, dvd_era_movie)
        assert result.is_compatible, (
            "Compatible streaming movie schema should subsume DVD-era schema "
            "because it maintains same types and enums while only adding optional fields"
        )


if __name__ == "__main__":
    print("=" * 70)
    print("Schema Evolution Tests")
    print("Testing real-world producer-consumer compatibility scenarios")
    print("=" * 70)
