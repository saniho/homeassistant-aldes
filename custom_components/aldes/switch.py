"""Support for Aldes switches."""
from __future__ import annotations
import logging
from datetime import datetime, timedelta

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import AldesEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Aldes switches from a config_entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Starting switch setup")

    switches: list[SwitchEntity] = []
    for product in coordinator.data:
        modem_id = product.get("modem")
        if not modem_id or modem_id == "N/A":
            continue

        indicator_data = product.get("indicator", {})

        # Create vacation mode switch if data is available
        if "date_debut_vac" in indicator_data:
            _LOGGER.debug(f"Creating vacation mode switch for {modem_id}")
            switches.append(AldesVacationModeSwitch(coordinator, entry, modem_id, product))

        # Create frost protection switch if data is available
        if "hors_gel" in indicator_data:
            _LOGGER.debug(f"Creating frost protection switch for {modem_id}")
            switches.append(AldesFrostProtectionSwitch(coordinator, entry, modem_id, product))

    async_add_entities(switches)


class AldesVacationModeSwitch(AldesEntity, SwitchEntity):
    """Represents the vacation mode switch for an Aldes product."""

    def __init__(
        self,
        coordinator,
        config_entry,
        modem_id,
        product,
    ):
        """Initialize the switch."""
        super().__init__(
            coordinator,
            config_entry,
            modem_id,
            product.get("reference"),
            modem_id,
        )
        self._attr_unique_id = f"{DOMAIN}_{modem_id}_vacation_switch"
        self._attr_name = "Aldes Vacation Mode"
        self._attr_icon = "mdi:calendar-clock"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        product_data = next(
            (p for p in self.coordinator.data if p.get("modem") == self.modem),
            None,
        )
        
        self._attr_is_on = False  # Default to off
        if product_data and product_data.get("indicator"):
            start_date_str = product_data["indicator"].get("date_debut_vac")
            end_date_str = product_data["indicator"].get("date_fin_vac")

            if start_date_str and end_date_str:
                try:
                    start_date = dt_util.parse_datetime(start_date_str.replace(" ", "T"))
                    end_date = dt_util.parse_datetime(end_date_str.replace(" ", "T"))
                    now = dt_util.utcnow()
                    
                    if start_date <= now <= end_date:
                        self._attr_is_on = True
                except (ValueError, TypeError):
                    pass  # Keep it off if dates are invalid

        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the vacation mode on."""
        # By default, set vacation for 7 days
        now = dt_util.utcnow()
        start_date = now
        end_date = now + timedelta(days=7)
        
        await self.coordinator.api.set_vacation_mode(self.modem, start_date, end_date)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the vacation mode off by sending the reset command."""
        await self.coordinator.api.set_vacation_mode(self.modem, None, None)
        await self.coordinator.async_request_refresh()


class AldesFrostProtectionSwitch(AldesEntity, SwitchEntity):
    """Represents the frost protection switch for an Aldes product."""

    def __init__(
        self,
        coordinator,
        config_entry,
        modem_id,
        product,
    ):
        """Initialize the switch."""
        super().__init__(
            coordinator,
            config_entry,
            modem_id,
            product.get("reference"),
            modem_id,
        )
        self._attr_unique_id = f"{DOMAIN}_{modem_id}_frost_protection_switch"
        self._attr_name = "Aldes Frost Protection"
        self._attr_icon = "mdi:snowflake-alert"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        product_data = next(
            (p for p in self.coordinator.data if p.get("modem") == self.modem),
            None,
        )
        
        if product_data and product_data.get("indicator"):
            # The switch is on if the mode is 'H' (Hors Gel)
            self._attr_is_on = product_data["indicator"].get("current_air_mode") == "H"
        else:
            self._attr_is_on = False
        
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn frost protection on by sending the 'H' command."""
        await self.coordinator.api.set_frost_protection(self.modem, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn frost protection off by sending the 'E' (Auto) command."""
        await self.coordinator.api.set_frost_protection(self.modem, False)
        await self.coordinator.async_request_refresh()
