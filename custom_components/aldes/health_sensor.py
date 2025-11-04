"""Health sensor for Aldes integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN
from .coordinator import AldesDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aldes health sensor."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([AldesHealthSensor(coordinator)], True)


class AldesHealthSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Aldes health sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "health"

    def __init__(self, coordinator: AldesDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api._username}_health"
        self._attr_name = "Aldes System Health"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return "OK" if self.coordinator.health_status else "ERROR"

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:check-circle" if self.coordinator.health_status else "mdi:alert-circle"
