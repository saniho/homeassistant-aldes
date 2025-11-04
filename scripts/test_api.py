#!/usr/bin/env python3
"""Script de test pour l'API Aldes."""
import asyncio
import aiohttp
import logging
import argparse
import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from custom_components.aldes.api import AldesApi

# Setup basic logging
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

async def test_api(username: str, password: str):
    """Teste les fonctionnalités principales de l'API."""
    _LOGGER.info("Démarrage des tests de l'API Aldes")
    _LOGGER.debug(f"Test avec l'utilisateur: {username}")

    async with aiohttp.ClientSession() as session:
        # The API key is handled inside the AldesApi class now
        api = AldesApi(username, password, session)

        try:
            # Test authentication
            _LOGGER.info("Test d'authentification...")
            await api.authenticate()
            _LOGGER.info("\033[92m✓ Authentification réussie\033[0m")

            # Test data fetching
            _LOGGER.info("\nRécupération des données...")
            data = await api.fetch_data()
            _LOGGER.info(f"\033[92m✓ Données récupérées: {len(data)} produits trouvés\033[0m")
            _LOGGER.info(f"\033[92m✓ Données JSON récupérées: {data} \033[0m")

            # Display data for each product
            for product in data:
                _LOGGER.info("\n[1mDétails du produit:[0m")
                _LOGGER.info(f"  ID: {product.get('modem', 'N/A')}")
                _LOGGER.info(f"  Type: {product.get('type', 'N/A')}")
                _LOGGER.info(f"  Nom: {product.get('name', 'N/A')}")
                _LOGGER.info(f"  Référence: {product.get('reference', 'N/A')}")
                _LOGGER.info(f"  Numéro de série: {product.get('serial_number', 'N/A')}")
                _LOGGER.info(f"  Connecté: {product.get('isConnected')}")

                indicator = product.get("indicator", {})
                if indicator:
                    _LOGGER.info("\n  [4mInformations générales:[0m")
                    _LOGGER.info(f"    Mode air actuel: {indicator.get('current_air_mode', 'N/A')}")
                    _LOGGER.info(f"    Mode eau actuel: {indicator.get('current_water_mode', 'N/A')}")
                    _LOGGER.info(f"    Température principale: {indicator.get('tmp_principal', 'N/A')}°C")
                    _LOGGER.info(f"    Quantité d'eau chaude: {indicator.get('qte_eau_chaude', 'N/A')}%")

                settings = indicator.get("settings")
                if settings:
                    _LOGGER.info("\n  [4mParamètres:[0m")
                    _LOGGER.info(f"    Nombre de personnes: {settings.get('people', 'N/A')}")

                thermostats = indicator.get("thermostats", [])
                if thermostats:
                    _LOGGER.info("\n  [4mThermostats:[0m")
                    for thermostat in thermostats:
                        thermostat_name = thermostat.get("Name") or f"Thermostat {thermostat.get('Number')}"
                        _LOGGER.info(f"    - {thermostat_name}:")
                        _LOGGER.info(f"      ID: {thermostat.get('ThermostatId', 'N/A')}")
                        _LOGGER.info(f"      Température actuelle: {thermostat.get('CurrentTemperature', 'N/A')}°C")
                        _LOGGER.info(f"      Température de consigne: {thermostat.get('TemperatureSet', 'N/A')}°C")

        except Exception as e:
            _LOGGER.error(f"\033[91m❌ Erreur lors des tests: {str(e)}\033[0m")
            # Optionally re-raise to see the full stack trace
            # raise
        else:
            _LOGGER.info("\n\033[92m✓ Tests terminés avec succès!\033[0m")

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Test de l'API Aldes")
    parser.add_argument("username", help="Nom d'utilisateur Aldes")
    parser.add_argument("password", help="Mot de passe Aldes")

    args = parser.parse_args()

    try:
        asyncio.run(test_api(args.username, args.password))
    except RuntimeError as e:
        # In Windows, the event loop might be closed before all transports are cleaned up.
        # This is a known issue and can be safely ignored if it happens at exit.
        if "Event loop is closed" in str(e):
            pass
        else:
            raise

if __name__ == "__main__":
    main()
