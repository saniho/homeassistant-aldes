"""Constants for aldes."""
from homeassistant.const import Platform

NAME = "Aldes"
DOMAIN = "aldes"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

MANUFACTURER = "Aldes"
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.SWITCH,
]

FRIENDLY_NAMES = {"TONE_AIR": "T.One® AIR", "TONE_AQUA_AIR": "T.One® AquaAIR"}

# Constantes pour le cache et retry
DEFAULT_SCAN_INTERVAL = 60  # Intervalle de mise à jour en secondes
CACHE_TTL = 300  # Durée de vie du cache en secondes (5 minutes)
MAX_RETRIES = 3  # Nombre maximum de tentatives
RETRY_DELAY = 60  # Délai maximum pour les retries en secondes
