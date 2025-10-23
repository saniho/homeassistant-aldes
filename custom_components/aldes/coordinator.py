"""Aldes"""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any
import async_timeout
from aiohttp import ClientError
import backoff

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AldesApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AldesDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Aldes data coordinator."""

    _API_TIMEOUT = 10
    _CACHE_TTL = timedelta(minutes=5)

    def __init__(self, hass: HomeAssistant, api: AldesApi):
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )
        self.api = api
        self._cache = {}
        self._last_update = None
        self._failed_updates = 0
        self._max_failed_updates = 3
        self.health_status = True

    @backoff.on_exception(
        backoff.expo,
        (ClientError, TimeoutError),
        max_tries=3,
        max_time=30,
    )
    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library with retry and cache."""
        now = dt_util.utcnow()

        # Utiliser le cache si disponible et valide
        if self._cache and self._last_update and (now - self._last_update) < self._CACHE_TTL:
            return self._cache

        try:
            async with async_timeout.timeout(self._API_TIMEOUT):
                data = await self.api.fetch_data()
                self._cache = data
                self._last_update = now
                self._failed_updates = 0
                self.health_status = True
                return data

        except Exception as exception:
            self._failed_updates += 1
            self.health_status = False

            if self._failed_updates >= self._max_failed_updates:
                _LOGGER.error("Multiple consecutive update failures: %s", exception)
            else:
                _LOGGER.warning("Update failed: %s", exception)

            if self._cache:
                _LOGGER.info("Using cached data due to update failure")
                return self._cache

            raise UpdateFailed(exception) from exception
