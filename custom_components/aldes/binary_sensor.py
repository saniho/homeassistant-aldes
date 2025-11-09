"""Support for the Aldes binary sensors."""
from __future__ import annotations
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import AldesEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Aldes binary sensors from a config_entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Starting binary sensor setup")

    binary_sensors: list[BinarySensorEntity] = []
    for product in coordinator.data:
        modem_id = product.get("modem")
        # Prevent creation of entities with invalid ID
        if not modem_id or modem_id == "N/A":
            _LOGGER.warning("Skipping product with invalid modem ID: %s", modem_id)
            continue

        _LOGGER.debug(f"Creating connectivity sensor for {modem_id}")
        binary_sensors.append(AldesConnectivitySensor(coordinator, entry, modem_id, product))

    async_add_entities(binary_sensors)


class AldesConnectivitySensor(AldesEntity, BinarySensorEntity):
    """Represents the connectivity status of an Aldes product."""

    def __init__(
        self,
        coordinator,
        config_entry,
        modem_id,
        product,
    ):
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            config_entry,
            modem_id,
            product.get("reference"),
            modem_id,
        )
        self._attr_unique_id = f"{DOMAIN}_{modem_id}_connectivity"
        self._attr_name = "Aldes Connection Status"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = super().extra_state_attributes or {}
        product_data = next(
            (p for p in self.coordinator.data if p.get("modem") == self.modem),
            None,
        )

        if product_data:
            attributes["product_type"] = product_data.get("type")
            attributes["product_reference"] = product_data.get("reference")
            attributes["latitude"] = product_data.get("gpsLatitude")
            attributes["longitude"] = product_data.get("gpsLongitude")
        
        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        product_data = next(
            (p for p in self.coordinator.data if p.get("modem") == self.modem),
            None,
        )
        
        if product_data:
            self._attr_is_on = product_data.get("isConnected", False)
        else:
            self._attr_is_on = False
        
        super()._handle_coordinator_update()
