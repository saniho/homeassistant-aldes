"""Support for the Aldes sensors."""
from __future__ import annotations
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, PEOPLE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER
from .entity import AldesEntity

_LOGGER = logging.getLogger(__name__)

# Describes the sensors that are not thermostats
PRODUCT_SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="qte_eau_chaude",
        name="Hot Water Level",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:water-percent",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="tmp_principal",
        name="Main Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="current_air_mode",
        name="Air Mode",
        icon="mdi:air-filter",
    ),
    SensorEntityDescription(
        key="current_water_mode",
        name="Water Mode",
        icon="mdi:water",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Aldes sensors from a config_entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Starting sensor setup")

    sensors: list[SensorEntity] = []
    for product in coordinator.data:
        modem_id = product.get("modem")
        if not modem_id:
            _LOGGER.warning("Skipping product with no modem ID: %s", product)
            continue

        _LOGGER.debug(f"Setting up sensors for product with modem ID: {modem_id}")

        indicator_data = product.get("indicator")
        if not indicator_data:
            continue

        # --- Product Sensors ---
        known_keys = {desc.key for desc in PRODUCT_SENSOR_DESCRIPTIONS}
        for description in PRODUCT_SENSOR_DESCRIPTIONS:
            if description.key in indicator_data:
                _LOGGER.debug(f"Creating sensor '{description.name}' for {modem_id}")
                sensors.append(
                    AldesProductSensor(coordinator, entry, modem_id, product, description)
                )

        # --- Settings Sensor ---
        if "settings" in indicator_data:
            _LOGGER.debug(f"Creating sensor 'Aldes Settings' for {modem_id}")
            sensors.append(AldesSettingsSensor(coordinator, entry, modem_id, product))

        # --- Thermostat Sensors ---
        if isinstance(indicator_data.get("thermostats"), list):
            for thermostat in indicator_data["thermostats"]:
                thermostat_id = thermostat.get("thermostatId")
                if thermostat_id:
                    thermostat_name = thermostat.get("Name") or f"Thermostat {thermostat_id}"
                    _LOGGER.debug(f"Creating thermostat sensor '{thermostat_name}' for {modem_id}")
                    sensors.append(
                        AldesThermostatSensor(coordinator, entry, modem_id, product, thermostat)
                    )

        # --- Log unhandled indicators ---
        for key, value in indicator_data.items():
            if key not in known_keys and key != "settings" and not isinstance(value, (dict, list)):
                _LOGGER.debug(
                    f"Unhandled indicator key found for {modem_id}: '{key}' with value: {value}. "
                    "Consider adding a sensor for it."
                )

    if not sensors:
        _LOGGER.warning("No sensors were created. Check API data and integration logic.")
    else:
        _LOGGER.debug(f"Adding {len(sensors)} sensors to Home Assistant")

    async_add_entities(sensors)


class AldesProductSensor(AldesEntity, SensorEntity):
    """Represents a sensor for an Aldes product."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator,
        config_entry,
        modem_id,
        product,
        description: SensorEntityDescription,
    ):
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            config_entry,
            modem_id,
            product.get("reference"),
            modem_id,
        )
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{modem_id}_{description.key}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        product_data = next(
            (p for p in self.coordinator.data if p.get("modem") == self.modem),
            None,
        )
        
        if (
            product_data
            and product_data.get("isConnected")
            and product_data.get("indicator")
        ):
            self._attr_native_value = product_data["indicator"].get(
                self.entity_description.key
            )
        else:
            self._attr_native_value = None
        
        super()._handle_coordinator_update()


class AldesSettingsSensor(AldesEntity, SensorEntity):
    """Represents a sensor for Aldes product settings."""

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
        self._attr_unique_id = f"{DOMAIN}_{modem_id}_settings"
        self._attr_name = "Aldes Settings"
        self._attr_icon = "mdi:cog"
        self._attr_native_unit_of_measurement = PEOPLE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = super().extra_state_attributes
        product_data = next(
            (p for p in self.coordinator.data if p.get("modem") == self.modem),
            None,
        )

        if (
            product_data
            and product_data.get("indicator")
            and "settings" in product_data["indicator"]
        ):
            attributes.update(product_data["indicator"]["settings"])
            
        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        product_data = next(
            (p for p in self.coordinator.data if p.get("modem") == self.modem),
            None,
        )
        
        if (
            product_data
            and product_data.get("isConnected")
            and product_data.get("indicator")
            and "settings" in product_data["indicator"]
        ):
            self._attr_native_value = product_data["indicator"]["settings"].get("people")
        else:
            self._attr_native_value = None
        
        super()._handle_coordinator_update()


class AldesThermostatSensor(AldesEntity, SensorEntity):
    """Define an Aldes thermostat sensor."""

    def __init__(
        self,
        coordinator,
        config_entry,
        modem_id,
        product,
        thermostat,
    ):
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            config_entry,
            modem_id,
            product.get("reference"),
            modem_id,
        )
        self.thermostat = thermostat
        self.thermostat_id = thermostat["thermostatId"]
        
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_unique_id = f"{DOMAIN}_{self.thermostat_id}_temperature"
        
        thermostat_name = self.thermostat.get("Name") or f"Thermostat {self.thermostat_id}"
        self._attr_name = f"{thermostat_name} Temperature"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info for the thermostat, grouped under the main product."""
        thermostat_name = self.thermostat.get("Name") or f"Thermostat {self.thermostat_id}"
        return DeviceInfo(
            identifiers={(DOMAIN, self.thermostat_id)},
            name=thermostat_name,
            manufacturer=MANUFACTURER,
            model="Thermostat",
            via_device=(DOMAIN, self.modem),  # Link to the main device
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        product_data = next(
            (p for p in self.coordinator.data if p.get("modem") == self.modem),
            None,
        )

        if (
            product_data
            and product_data.get("isConnected")
            and product_data.get("indicator")
            and isinstance(product_data["indicator"].get("thermostats"), list)
        ):
            thermostat_data = next(
                (t for t in product_data["indicator"]["thermostats"] if t.get("thermostatId") == self.thermostat_id),
                None,
            )
            
            if thermostat_data and "CurrentTemperature" in thermostat_data:
                self._attr_native_value = round(thermostat_data["CurrentTemperature"], 1)
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = None

        super()._handle_coordinator_update()
