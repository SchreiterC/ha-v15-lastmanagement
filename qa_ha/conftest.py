"""Real Home Assistant fixtures, isolated from every production device.

Run only with Home Assistant 2026.11.x and pytest-homeassistant-custom-component.
"""

import pytest


@pytest.fixture(autouse=True)
def allow_custom_component(enable_custom_integrations):
    """Register the local test copy of V15 with Home Assistant's loader."""
    return None
