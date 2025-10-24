"""Aldes"""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any
import async_timeout
from aiohttp import ClientError, ClientTimeout
import backoff

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AldesApi
from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CACHE_TTL,
    MAX_RETRIES,
    RETRY_DELAY
)

_LOGGER = logging.getLogger(__name__)

class AldesDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Aldes data coordinator."""

    def __init__(self, hass: HomeAssistant, api: AldesApi) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self._failed_updates = 0
        self.health_status = True

    @backoff.on_exception(
        backoff.expo,
        (ClientError, TimeoutError),
        max_tries=MAX_RETRIES,
        max_time=RETRY_DELAY,
        logger=_LOGGER,
    )
    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library with enhanced retry and cache."""
        try:
            async with async_timeout.timeout(self.api._REQUEST_TIMEOUT):
                data = await self.api.fetch_data()
                self._failed_updates = 0
                self.health_status = True
                return data

        except Exception as exception:
            self._failed_updates += 1
            self.health_status = False

            if self._failed_updates >= MAX_RETRIES:
                _LOGGER.error("Multiple consecutive update failures: %s", exception)
            else:
                _LOGGER.warning("Update failure %d/%d: %s",
                              self._failed_updates, MAX_RETRIES, exception)

            # L'API gère maintenant son propre cache, on laisse remonter l'erreur
            # si elle ne peut pas fournir de données cachées
            raise UpdateFailed(exception) from exception
