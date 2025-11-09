"""Support for the Aldes climate platform."""
from __future__ import annotations
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER
from .entity import AldesEntity

_LOGGER = logging.getLogger(__name__)

# Temperature range for the device
MIN_TEMP = 16.0
MAX_TEMP = 31.0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Aldes climate entities from a config_entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Starting climate setup")

    climates: list[AldesClimateEntity] = []
    for product in coordinator.data:
        modem_id = product.get("modem")
        # Prevent creation of entities with invalid ID
        if not modem_id or modem_id == "N/A":
            _LOGGER.warning("Skipping product with invalid modem ID: %s", modem_id)
            continue

        if product.get("indicator") and isinstance(
            product["indicator"].get("thermostats"), list
        ):
            for thermostat in product["indicator"]["thermostats"]:
                thermostat_id = thermostat.get("ThermostatId")
                if thermostat_id:
                    climates.append(
                        AldesClimateEntity(coordinator, entry, modem_id, product, thermostat)
                    )

    _LOGGER.debug(f"Adding {len(climates)} climate entities")
    async_add_entities(climates)


class AldesClimateEntity(AldesEntity, ClimateEntity):
    """Define an Aldes climate entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        config_entry,
        modem_id,
        product,
        thermostat,
    ):
        """Initialize the climate entity."""
        super().__init__(
            coordinator,
            config_entry,
            modem_id,  # Use modem as the primary ID
            product.get("reference"),
            modem_id,
        )
        self.thermostat = thermostat
        self.thermostat_id = thermostat["ThermostatId"]

        # Static attributes
        self._attr_unique_id = f"{DOMAIN}_{self.thermostat_id}_climate"
        thermostat_name = self.thermostat.get("Name") or f"Thermostat {self.thermostat_id}"
        self._attr_name = thermostat_name
        
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_min_temp = MIN_TEMP
        self._attr_max_temp = MAX_TEMP
        self._attr_target_temperature_step = 0.5
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_OFF
        )
        self._enable_turn_on_off_backwards_compatibility = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info for the thermostat, grouped under the main product."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.modem)},
            name=self.coordinator.data[0].get("name", "Aldes Product"),
            manufacturer=MANUFACTURER,
            model=self.reference,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        product_data = next(
            (p for p in self.coordinator.data if p.get("modem") == self.modem),
            None,
        )

        if not (product_data and product_data.get("isConnected")):
            self._attr_available = False
            return
        
        self._attr_available = True

        # Update HVAC mode
        air_mode = product_data.get("indicator", {}).get("current_air_mode")
        if air_mode in ["A"]:
            self._attr_hvac_mode = HVACMode.OFF
        elif air_mode in ["B", "C"]:
            self._attr_hvac_mode = HVACMode.HEAT
        elif air_mode in ["F", "G"]:
            self._attr_hvac_mode = HVACMode.COOL
        elif air_mode in ["D", "E", "H", "I"]:
            self._attr_hvac_mode = HVACMode.AUTO
        else:
            self._attr_hvac_mode = HVACMode.OFF

        # Update temperatures
        thermostats = product_data.get("indicator", {}).get("thermostats", [])
        thermostat_data = next(
            (t for t in thermostats if t.get("ThermostatId") == self.thermostat_id),
            None,
        )

        if thermostat_data:
            self._attr_current_temperature = thermostat_data.get("CurrentTemperature")
            self._attr_target_temperature = thermostat_data.get("TemperatureSet")
        
        super()._handle_coordinator_update()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        _LOGGER.debug(
            f"Setting temperature for {self.thermostat_id} to {temperature}"
        )
        await self.coordinator.api.set_target_temperature(
            self.modem,
            self.thermostat_id,
            self.thermostat.get("Name"),
            temperature,
        )
        # Optimistically update the state
        self._attr_target_temperature = temperature
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        _LOGGER.debug(f"Setting HVAC mode to {hvac_mode}")
        
        mode_map = {
            HVACMode.OFF: "A",
            HVACMode.HEAT: "B",
            HVACMode.COOL: "F",
            HVACMode.AUTO: "E", # Defaulting AUTO to 'E'
        }
        
        target_mode = mode_map.get(hvac_mode)
        if target_mode:
            await self.coordinator.api.change_mode(self.modem, target_mode)
            # Optimistically update the state
            self._attr_hvac_mode = hvac_mode
            self.async_write_ha_state()
