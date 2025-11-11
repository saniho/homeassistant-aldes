#!/usr/bin/env python3
"""Script de test pour l'API Aldes."""
import asyncio
import aiohttp
import logging
import argparse
import os
import sys
import json
from datetime import datetime, timezone

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from custom_components.aldes.api import AldesApi

# Setup basic logging
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

def get_version_from_manifest():
    """Reads the version from the manifest.json file."""
    try:
        manifest_path = os.path.join(project_root, 'custom_components', 'aldes', 'manifest.json')
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            return manifest.get("version", "unknown")
    except (FileNotFoundError, json.JSONDecodeError):
        return "unknown"

async def test_api(username: str, password: str):
    """Teste les fonctionnalités principales de l'API."""
    version = get_version_from_manifest()
    _LOGGER.info(f"Démarrage des tests de l'API Aldes (Version de l'intégration: {version})")
    _LOGGER.debug(f"Test avec l'utilisateur: {username}")

    async with aiohttp.ClientSession() as session:
        api = AldesApi(username, password, session)

        try:
            # Test authentication
            _LOGGER.info("Test d'authentification...")
            await api.authenticate()
            _LOGGER.info("\033[92m✓ Authentification réussie\033[0m")

            # Test data fetching
            _LOGGER.info("\nRécupération des données...")
            data = await api.fetch_data()
            
            if not data:
                _LOGGER.warning("Aucune donnée n'a été récupérée de l'API.")
                return

            #_LOGGER.info(f"\033[92m✓ Données récupérées: {len(data)} produits trouvés\033[0m")

            # --- Raw JSON Output (Wrapper Output) ---
            #_LOGGER.info("\n[1m--- Début des données brutes (sortie du wrapper) ---\033[0m")
            #print(json.dumps(data, indent=2))
            #_LOGGER.info("[1m--- Fin des données brutes ---\033[0m")


            # Display formatted data for each product
            for product in data:
                _LOGGER.info("\n[1mDétails du produit:[0m")
                _LOGGER.info(f"  ID: {product.get('modem', 'N/A')}")
                _LOGGER.info(f"  Type: {product.get('type', 'N/A')}")
                _LOGGER.info(f"  Nom: {product.get('name', 'N/A')}")
                _LOGGER.info(f"  Référence: {product.get('reference', 'N/A')}")

                # Display connection status and last update date
                is_connected = product.get('isConnected')
                connection_status = "\033[92mConnecté\033[0m" if is_connected else "\033[91mDéconnecté\033[0m"
                _LOGGER.info(f"  Statut: {connection_status}")
                _LOGGER.info(f"  Dernière mise à jour des données: {product.get('lastUpdatedDate', 'N/A')}")

                indicator = product.get("indicator", {})
                if indicator:
                    _LOGGER.info("\n  [4mInformations générales:[0m")
                    _LOGGER.info(f"    Mode air actuel: {indicator.get('current_air_mode', 'N/A')}")
                    _LOGGER.info(f"    Mode eau actuel: {indicator.get('current_water_mode', 'N/A')}")
                    _LOGGER.info(f"    Température principale: {indicator.get('tmp_principal', 'N/A')}°C")
                    _LOGGER.info(f"    Quantité d'eau chaude: {indicator.get('qte_eau_chaude', 'N/A')}%")
                    
                    hors_gel_status = "Actif" if indicator.get('hors_gel') else "Inactif"
                    _LOGGER.info(f"    Mode hors gel: {hors_gel_status}")

                    # Vacation mode status and dates
                    vac_start_str = indicator.get('date_debut_vac')
                    vac_end_str = indicator.get('date_fin_vac')
                    
                    vacation_status = "Inactif"
                    if vac_start_str and vac_end_str:
                        try:
                            # Convert to datetime objects, handling 'Z' for UTC
                            start_date = datetime.fromisoformat(vac_start_str.replace(' ', 'T').replace('Z', '+00:00'))
                            end_date = datetime.fromisoformat(vac_end_str.replace(' ', 'T').replace('Z', '+00:00'))
                            now_utc = datetime.now(timezone.utc)

                            if start_date <= now_utc <= end_date:
                                vacation_status = "\033[92mActif\033[0m" # Green for active
                            else:
                                vacation_status = "\033[91mInactif\033[0m" # Red for inactive
                        except (ValueError, TypeError):
                            _LOGGER.warning(f"Could not parse vacation dates: {vac_start_str}, {vac_end_str}")
                            vacation_status = "Dates invalides"

                    _LOGGER.info(f"    Mode vacances: {vacation_status}")
                    if vac_start_str:
                        _LOGGER.info(f"      Début des vacances: {vac_start_str}")
                    if vac_end_str:
                        _LOGGER.info(f"      Fin des vacances: {vac_end_str}")


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
            
            _LOGGER.info("\n\033[92m✓ Tests terminés avec succès!\033[0m")

        except Exception as e:
            _LOGGER.error(f"\033[91m❌ Erreur lors des tests: {str(e)}\033[0m")
            # Optionally re-raise to see the full stack trace
            # raise

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
