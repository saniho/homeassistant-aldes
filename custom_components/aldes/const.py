"""Constants for aldes."""
from homeassistant.const import Platform

NAME = "Aldes"
DOMAIN = "aldes"
VERSION = "0.0.1"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

MANUFACTURER = "Aldes"
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.CLIMATE]

# Constants pour le cache et retry
DEFAULT_SCAN_INTERVAL = 60
CACHE_TTL = 300  # 5 minutes en secondes
MAX_RETRIES = 3
RETRY_DELAY = 30  # 30 secondes

FRIENDLY_NAMES = {"TONE_AIR": "T.One® AIR", "TONE_AQUA_AIR": "T.One® AquaAIR"}
