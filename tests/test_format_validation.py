"""Tests for format validation constraints."""

import pytest
from jsound.core.subsumption import SubsumptionChecker, SolverConfig


class TestFormatValidation:
    """Test format validation constraints and subsumption."""

    @pytest.fixture
    def checker(self):
        """Create a subsumption checker."""
        config = SolverConfig(timeout=10)
        return SubsumptionChecker(config)

    @pytest.mark.subsumption
    def test_same_format_subsumption(self, checker):
        """Test that same format schemas subsume each other."""
        producer = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email"}},
            "required": ["email"],
        }

        consumer = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email"}},
            "required": ["email"],
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, "Identical format schemas should be compatible"

    @pytest.mark.subsumption
    def test_format_to_string_subsumption(self, checker):
        """Test that format-constrained strings subsume plain strings."""
        producer = {
            "type": "object",
            "properties": {
                "contact": {"type": "string", "format": "email"},
                "website": {"type": "string", "format": "uri"},
                "created": {"type": "string", "format": "date-time"},
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "contact": {"type": "string"},
                "website": {"type": "string"},
                "created": {"type": "string"},
            },
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Format-validated producer should subsume string-only consumer"
        )

    @pytest.mark.anti_subsumption
    def test_string_to_format_anti_subsumption(self, checker):
        """Test that plain strings do not subsume format-constrained strings."""
        producer = {
            "type": "object",
            "properties": {"email": {"type": "string"}},
            "required": ["email"],
        }

        consumer = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email"}},
            "required": ["email"],
        }

        result = checker.check_subsumption(producer, consumer)
        assert not result.is_compatible, (
            "Plain string producer should not subsume format-constrained consumer"
        )
        assert result.counterexample is not None, "Should provide counterexample"

    @pytest.mark.anti_subsumption
    def test_different_formats_incompatible(self, checker):
        """Test that different formats are incompatible."""
        producer = {
            "type": "object",
            "properties": {"contact": {"type": "string", "format": "email"}},
            "required": ["contact"],
        }

        consumer = {
            "type": "object",
            "properties": {"contact": {"type": "string", "format": "uri"}},
            "required": ["contact"],
        }

        result = checker.check_subsumption(producer, consumer)
        assert not result.is_compatible, "Email format should not subsume URI format"

    @pytest.mark.subsumption
    def test_multiple_format_constraints(self, checker):
        """Test complex schema with multiple format constraints."""
        producer = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "format": "uuid"},
                "email": {"type": "string", "format": "email"},
                "profile_url": {"type": "string", "format": "uri"},
                "birth_date": {"type": "string", "format": "date"},
                "last_login": {"type": "string", "format": "date-time"},
                "login_time": {"type": "string", "format": "time"},
            },
            "required": ["user_id", "email"],
        }

        consumer = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string"},
                "profile_url": {"type": "string"},
                "birth_date": {"type": "string"},
                "last_login": {"type": "string"},
                "login_time": {"type": "string"},
            },
            "required": ["user_id", "email"],
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer with multiple format constraints should subsume string-only consumer"
        )

    @pytest.mark.subsumption
    def test_format_with_additional_constraints(self, checker):
        """Test format combined with other string constraints."""
        producer = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "minLength": 10,
                    "maxLength": 100,
                }
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "minLength": 5,
                    "maxLength": 200,
                }
            },
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer with stricter length constraints should subsume consumer with looser constraints"
        )

    @pytest.mark.subsumption
    def test_ipv4_format_validation(self, checker):
        """Test IPv4 format validation."""
        producer = {
            "type": "object",
            "properties": {"server_ip": {"type": "string", "format": "ipv4"}},
        }

        consumer = {"type": "object", "properties": {"server_ip": {"type": "string"}}}

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, "IPv4 format should subsume plain string"

    @pytest.mark.subsumption
    def test_ipv6_format_validation(self, checker):
        """Test IPv6 format validation."""
        producer = {
            "type": "object",
            "properties": {"server_ipv6": {"type": "string", "format": "ipv6"}},
        }

        consumer = {"type": "object", "properties": {"server_ipv6": {"type": "string"}}}

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, "IPv6 format should subsume plain string"

    @pytest.mark.anti_subsumption
    def test_ipv4_ipv6_incompatible(self, checker):
        """Test that IPv4 and IPv6 formats are incompatible."""
        producer = {
            "type": "object",
            "properties": {"ip_address": {"type": "string", "format": "ipv4"}},
        }

        consumer = {
            "type": "object",
            "properties": {"ip_address": {"type": "string", "format": "ipv6"}},
        }

        result = checker.check_subsumption(producer, consumer)
        assert not result.is_compatible, "IPv4 and IPv6 formats should be incompatible"

    @pytest.mark.subsumption
    def test_custom_format_handling(self, checker):
        """Test handling of custom/unknown formats."""
        producer = {
            "type": "object",
            "properties": {
                "custom_field": {"type": "string", "format": "custom-format-xyz"}
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "custom_field": {"type": "string", "format": "custom-format-xyz"}
            },
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, "Same custom format should be compatible"

    @pytest.mark.anti_subsumption
    def test_different_custom_formats_incompatible(self, checker):
        """Test that different custom formats are incompatible."""
        producer = {
            "type": "object",
            "properties": {"field": {"type": "string", "format": "custom-format-a"}},
        }

        consumer = {
            "type": "object",
            "properties": {"field": {"type": "string", "format": "custom-format-b"}},
        }

        result = checker.check_subsumption(producer, consumer)
        assert not result.is_compatible, (
            "Different custom formats should be incompatible"
        )

    @pytest.mark.subsumption
    def test_format_self_subsumption(self, checker):
        """Test that format-constrained schemas subsume themselves."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "email": {"type": "string", "format": "email"},
                "website": {"type": "string", "format": "uri"},
                "created_at": {"type": "string", "format": "date-time"},
            },
            "required": ["id", "email"],
        }

        result = checker.check_subsumption(schema, schema)
        assert result.is_compatible, "Any schema should subsume itself"


class TestFormatEdgeCases:
    """Test edge cases for format validation."""

    @pytest.fixture
    def checker(self):
        config = SolverConfig(timeout=10)
        return SubsumptionChecker(config)

    @pytest.mark.subsumption
    def test_optional_format_fields(self, checker):
        """Test format validation on optional fields."""
        producer = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "website": {"type": "string", "format": "uri"},
            },
            "required": ["email"],
        }

        consumer = {
            "type": "object",
            "properties": {"email": {"type": "string"}, "website": {"type": "string"}},
            "required": ["email"],
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Format validation on optional fields should work correctly"
        )

    @pytest.mark.subsumption
    def test_format_in_nested_objects(self, checker):
        """Test format validation in nested object structures."""
        producer = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "contact": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string", "format": "email"},
                                "phone": {"type": "string"},
                            },
                        }
                    },
                }
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "contact": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                            },
                        }
                    },
                }
            },
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Format validation should work in nested structures"
        )

    @pytest.mark.subsumption
    def test_format_with_anyof(self, checker):
        """Test format validation combined with anyOf."""
        producer = {
            "type": "object",
            "properties": {
                "contact": {
                    "anyOf": [
                        {"type": "string", "format": "email"},
                        {"type": "string", "format": "uri"},
                    ]
                }
            },
        }

        consumer = {"type": "object", "properties": {"contact": {"type": "string"}}}

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "anyOf with format constraints should subsume plain string"
        )
