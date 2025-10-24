"""Tests for the Aldes Coordinator."""
import asyncio
import pytest
from unittest.mock import Mock, patch
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.aldes.coordinator import AldesDataUpdateCoordinator
from custom_components.aldes.api import AldesApi

@pytest.fixture
def coordinator():
    """Create a test coordinator instance."""
    hass = Mock(spec=HomeAssistant)
    api = Mock(spec=AldesApi)
    return AldesDataUpdateCoordinator(hass, api)

@pytest.mark.asyncio
async def test_successful_update(coordinator):
    """Test successful data update."""
    test_data = {"temperature": 21, "mode": "heat"}
    coordinator.api.fetch_data = asyncio.coroutine(lambda: test_data)

    data = await coordinator._async_update_data()
    assert data == test_data
    assert coordinator.health_status is True
    assert coordinator._failed_updates == 0

@pytest.mark.asyncio
async def test_failed_update(coordinator):
    """Test failed data update."""
    coordinator.api.fetch_data = asyncio.coroutine(lambda: raise_(Exception("API Error")))

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.health_status is False
    assert coordinator._failed_updates == 1

@pytest.mark.asyncio
async def test_multiple_failed_updates(coordinator):
    """Test multiple failed updates."""
    coordinator.api.fetch_data = asyncio.coroutine(lambda: raise_(Exception("API Error")))

    for _ in range(3):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    assert coordinator.health_status is False
    assert coordinator._failed_updates == 3

def raise_(ex):
    """Helper to raise exceptions in lambda functions."""
    raise ex
