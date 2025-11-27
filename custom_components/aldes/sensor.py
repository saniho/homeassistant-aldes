"""Support for the Aldes sensors."""
from __future__ import annotations
import logging
from typing import Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfPressure, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import AldesDataUpdateCoordinator
from .entity import AldesEntity

_LOGGER = logging.getLogger(__name__)

# Describes the sensors that are not thermostats
PRODUCT_SENSOR_DESCRIPTIONS: Final[tuple[SensorEntityDescription, ...]] = (
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
    SensorEntityDescription(
        key="date_debut_vac",
        name="Vacation Start",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-start",
    ),
    SensorEntityDescription(
        key="date_fin_vac",
        name="Vacation End",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-end",
    ),
)

THERMOSTAT_SENSOR_DESCRIPTIONS: Final[tuple[SensorEntityDescription, ...]] = (
    SensorEntityDescription(
        key="CurrentTemperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="CurrentHumidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Aldes sensors from a config_entry."""
    coordinator: AldesDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Starting sensor setup")

    sensors: list[SensorEntity] = []
    # Prevent creating entities for the same modem_id multiple times
    processed_modem_ids = set()

    for product in coordinator.data:
        modem_id = product.get("modem")
        if not modem_id or modem_id == "N/A" or modem_id in processed_modem_ids:
            if modem_id in processed_modem_ids:
                _LOGGER.debug("Skipping already processed modem ID: %s", modem_id)
            else:
                _LOGGER.warning("Skipping product with invalid modem ID: %s", modem_id)
            continue
        
        processed_modem_ids.add(modem_id)
        _LOGGER.debug("Setting up sensors for product with modem ID: %s", modem_id)

        indicator_data = product.get("indicator")
        if not indicator_data:
            _LOGGER.debug("No indicator data for modem ID: %s", modem_id)
            continue

        # --- Product Sensors ---
        for description in PRODUCT_SENSOR_DESCRIPTIONS:
            if description.key in indicator_data and indicator_data[description.key] is not None:
                sensors.append(
                    AldesProductSensor(coordinator, entry, modem_id, product, description)
                )

        # --- Settings Sensor ---
        if "settings" in indicator_data:
            sensors.append(AldesSettingsSensor(coordinator, entry, modem_id, product))

        # --- Thermostat Sensors ---
        if isinstance(indicator_data.get("thermostats"), list):
            for thermostat in indicator_data["thermostats"]:
                thermostat_id = thermostat.get("thermostatId")
                if not thermostat_id:
                    _LOGGER.warning("Skipping thermostat with no ID for modem %s", modem_id)
                    continue
                
                for description in THERMOSTAT_SENSOR_DESCRIPTIONS:
                    if description.key in thermostat:
                        sensors.append(
                            AldesThermostatSensor(
                                coordinator, entry, modem_id, product, thermostat, description
                            )
                        )

    if not sensors:
        _LOGGER.warning("No sensors were created. Check API data and integration logic.")
    else:
        _LOGGER.info("Adding %s Aldes sensors", len(sensors))

    async_add_entities(sensors)


class AldesProductSensor(AldesEntity, SensorEntity):
    """Represents a sensor for an Aldes product."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: AldesDataUpdateCoordinator,
        config_entry: ConfigEntry,
        modem_id: str,
        product: dict,
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
        product_data = self.coordinator.get_product(self.modem)
        
        if (
            product_data
            and product_data.get("isConnected")
            and (indicator_data := product_data.get("indicator"))
        ):
            value = indicator_data.get(self.entity_description.key)
            if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP and isinstance(value, str):
                try:
                    self._attr_native_value = dt_util.parse_datetime(value.replace(" ", "T"))
                except (ValueError, TypeError):
                    self._attr_native_value = None
            else:
                self._attr_native_value = value
        else:
            self._attr_native_value = None
        
        super()._handle_coordinator_update()


class AldesSettingsSensor(AldesEntity, SensorEntity):
    """Represents a sensor for Aldes product settings."""

    def __init__(
        self,
        coordinator: AldesDataUpdateCoordinator,
        config_entry: ConfigEntry,
        modem_id: str,
        product: dict,
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
        self._attr_icon = "mdi:account-group"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        attributes = super().extra_state_attributes or {}
        product_data = self.coordinator.get_product(self.modem)

        if product_data and (indicator_data := product_data.get("indicator")):
            if "settings" in indicator_data:
                attributes.update(indicator_data["settings"])
        
        if self.registry_entry and self.registry_entry.device_id:
            attributes["device_id"] = self.registry_entry.device_id
            
        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        product_data = self.coordinator.get_product(self.modem)
        
        if (
            product_data
            and product_data.get("isConnected")
            and (indicator_data := product_data.get("indicator"))
            and "settings" in indicator_data
        ):
            people = indicator_data["settings"].get("people")
            if people is not None:
                try:
                    self._attr_native_value = int(people) + 2
                except (ValueError, TypeError):
                    self._attr_native_value = people
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = None
        
        super()._handle_coordinator_update()


class AldesThermostatSensor(AldesEntity, SensorEntity):
    """Define an Aldes thermostat sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: AldesDataUpdateCoordinator,
        config_entry: ConfigEntry,
        modem_id: str,
        product: dict,
        thermostat: dict,
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
        self.thermostat_id = thermostat["thermostatId"]
        
        thermostat_name = thermostat.get("Name") or f"Thermostat {self.thermostat_id}"
        self._attr_name = f"{thermostat_name} {description.name}"
        self._attr_unique_id = f"{DOMAIN}_{self.thermostat_id}_{description.key}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        product_data = self.coordinator.get_product(self.modem)
        thermostat_data = None

        if (
            product_data
            and product_data.get("isConnected")
            and (indicator_data := product_data.get("indicator"))
            and isinstance(indicator_data.get("thermostats"), list)
        ):
            thermostat_data = next(
                (t for t in indicator_data["thermostats"] if t.get("thermostatId") == self.thermostat_id),
                None,
            )
        
        if thermostat_data and self.entity_description.key in thermostat_data:
            value = thermostat_data[self.entity_description.key]
            self._attr_native_value = round(value, 1) if isinstance(value, (int, float)) else value
        else:
            self._attr_native_value = None

        super()._handle_coordinator_update()
