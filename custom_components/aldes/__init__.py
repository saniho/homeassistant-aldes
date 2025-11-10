"""
Custom integration to integrate Aldes with Home Assistant.

For more details about this integration, please refer to
https://github.com/saniho/homeassistant-aldes
"""
import json
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import AldesApi
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN, PLATFORMS
from .coordinator import AldesDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Aldes from a config entry."""
    
    # Read the integration version from the manifest
    version = "unknown"
    manifest_path = Path(hass.config.path(f"custom_components/{DOMAIN}/manifest.json"))
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text())
            version = manifest.get("version", "unknown")
        except (json.JSONDecodeError, FileNotFoundError):
            # Handle cases where manifest is malformed or not found
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
    return True
