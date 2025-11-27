"""
Custom integration to integrate Aldes with Home Assistant.

For more details about this integration, please refer to
https://github.com/guix77/homeassistant-aldes
"""
import json
from pathlib import Path
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client, config_validation as cv, device_registry as dr

from .api import AldesApi
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN, PLATFORMS
from .coordinator import AldesDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service definitions
SERVICE_SET_VACATION_DATES = "set_vacation_dates"
SERVICE_FORCE_REFRESH = "force_refresh"
ATTR_DEVICE_ID = "device_id"
ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"

SERVICE_SET_VACATION_DATES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_START_DATE): cv.datetime,
        vol.Optional(ATTR_END_DATE): cv.datetime,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Aldes from a config entry."""
    
    # Read the integration version from the manifest asynchronously
    version = "unknown"
    manifest_path = Path(hass.config.path(f"custom_components/{DOMAIN}/manifest.json"))
    if manifest_path.is_file():
        try:
            manifest_text = await hass.async_add_executor_job(manifest_path.read_text)
            manifest = json.loads(manifest_text)
            version = manifest.get("version", "unknown")
        except (json.JSONDecodeError, FileNotFoundError):
            _LOGGER.error("Could not read version from manifest.json")
            pass

    api = AldesApi(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        aiohttp_client.async_get_clientsession(hass),
    )
    coordinator = AldesDataUpdateCoordinator(hass, api, version)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    
    # Use the PLATFORMS constant from const.py
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    await coordinator.async_request_refresh()

    # Register the service to set vacation dates
    async def handle_set_vacation_dates(call):
        device_id = call.data.get(ATTR_DEVICE_ID)
        start_date_dt = call.data.get(ATTR_START_DATE)
        end_date_dt = call.data.get(ATTR_END_DATE)

        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get(device_id)

        if not device_entry:
            _LOGGER.error(f"Service call: Device with ID {device_id} not found.")
            return

        modem_id = None
        for identifier_tuple in device_entry.identifiers:
            if identifier_tuple[0] == DOMAIN:
                modem_id = identifier_tuple[1]
                break

        if not modem_id:
            _LOGGER.error(f"Service call: Modem ID not found for device {device_id}.")
            return

        _LOGGER.debug(f"Service call: Setting vacation mode for {modem_id} with start={start_date_dt}, end={end_date_dt}")
        await coordinator.api.set_vacation_mode(modem_id, start_date_dt, end_date_dt)
        await coordinator.async_request_refresh() # Refresh data to update states

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VACATION_DATES,
        handle_set_vacation_dates,
        schema=SERVICE_SET_VACATION_DATES_SCHEMA,
    )

    # Register the service to force refresh
    async def handle_force_refresh(call):
        """Handle the service call."""
        _LOGGER.debug("Service call: Forcing refresh of Aldes data, bypassing cache")
        await coordinator.async_force_refresh_data()

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_REFRESH,
        handle_force_refresh,
    )

    return True
