"""Real-world schema subsumption tests."""

import pytest
from src.jsound.api import JSoundAPI


@pytest.fixture
def api():
    """API instance for testing."""
    return JSoundAPI()


@pytest.fixture
def real_world_schemas():
    """Real-world schema examples."""
    return {
        "user_strict": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "age": {"type": "integer", "minimum": 0, "maximum": 120},
            },
            "required": ["name", "email", "age"],
            "additionalProperties": False,
        },
        "user_loose": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name", "email"],
        },
    }


@pytest.mark.real_world
@pytest.mark.subsumption
def test_user_profile_subsumption(api, real_world_schemas):
    """Test user profile subsumption."""
    result = api.check_subsumption(
        real_world_schemas["user_strict"], real_world_schemas["user_loose"]
    )
    assert result.is_compatible, (
        "Strict user profile should be subsumed by loose profile"
    )


@pytest.mark.real_world
@pytest.mark.anti_subsumption
def test_user_profile_anti_subsumption(api, real_world_schemas):
    """Test user profile anti-subsumption."""
    result = api.check_subsumption(
        real_world_schemas["user_loose"], real_world_schemas["user_strict"]
    )
    assert not result.is_compatible, "Should not be subsumed due to constraint conflicts"
