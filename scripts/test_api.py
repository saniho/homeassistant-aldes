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

from custom_components.aldes.api import AldesApi, AuthenticationException

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
    _LOGGER.info(f"Utilisateur: {username}")

    async with aiohttp.ClientSession() as session:
        api = AldesApi(username, password, session)

        try:
            # L'authentification est maintenant gérée automatiquement par le premier appel.
            _LOGGER.info("Récupération des données des produits...")
            data = await api.fetch_data()
            
            if not data:
                _LOGGER.warning("Aucune donnée n'a été récupérée. Vérifiez vos identifiants ou votre connexion.")
                return

            _LOGGER.info(f"\033[92m✓ Données récupérées: {len(data)} produit(s) trouvé(s)\033[0m")

            # Display formatted data for each product
            for product in data:
                _LOGGER.info("\n[1mDétails du produit:[0m")
                _LOGGER.info(f"  ID: {product.get('modem', 'N/A')}")
                _LOGGER.info(f"  Type: {product.get('type', 'N/A')}")
                _LOGGER.info(f"  Nom: {product.get('name', 'N/A')}")
                _LOGGER.info(f"  Référence: {product.get('reference', 'N/A')}")

                is_connected = product.get('isConnected')
                connection_status = "\033[92mConnecté\033[0m" if is_connected else "\033[91mDéconnecté\033[0m"
                _LOGGER.info(f"  Statut: {connection_status}")
                _LOGGER.info(f"  Dernière mise à jour: {product.get('lastUpdatedDate', 'N/A')}")

                indicator = product.get("indicator", {})
                if indicator:
                    _LOGGER.info("\n  [4mInformations générales:[0m")
                    _LOGGER.info(f"    Mode air: {indicator.get('current_air_mode', 'N/A')}")
                    _LOGGER.info(f"    Mode eau: {indicator.get('current_water_mode', 'N/A')}")
                    _LOGGER.info(f"    Température principale: {indicator.get('tmp_principal', 'N/A')}°C")
                    _LOGGER.info(f"    Quantité d'eau chaude: {indicator.get('qte_eau_chaude', 'N/A')}%")
                    
                    hors_gel_status = "Actif" if indicator.get('hors_gel') else "Inactif"
                    _LOGGER.info(f"    Mode hors gel: {hors_gel_status}")

                    vac_start_str = indicator.get('date_debut_vac')
                    vac_end_str = indicator.get('date_fin_vac')
                    vacation_status = "Inactif"
                    if vac_start_str and vac_end_str:
                        try:
                            start_date = datetime.fromisoformat(vac_start_str.replace('Z', '+00:00'))
                            end_date = datetime.fromisoformat(vac_end_str.replace('Z', '+00:00'))
                            if start_date <= datetime.now(timezone.utc) <= end_date:
                                vacation_status = "\033[92mActif\033[0m"
                        except (ValueError, TypeError):
                            vacation_status = "Dates invalides"
                    
                    _LOGGER.info(f"    Mode vacances: {vacation_status}")
                    if vac_start_str: _LOGGER.info(f"      Début: {vac_start_str}")
                    if vac_end_str: _LOGGER.info(f"      Fin: {vac_end_str}")

                    thermostats = indicator.get("thermostats", [])
                    if thermostats:
                        _LOGGER.info("\n  [4mThermostats:[0m")
                        for th in thermostats:
                            thermostat_id = th.get('ThermostatId', 'N/A')
                            name = th.get("Name") or f"Thermostat {th.get('Number')}"
                            _LOGGER.info(f"    - {name} (ID: {thermostat_id}): {th.get('CurrentTemperature', 'N/A')}°C (Consigne: {th.get('TemperatureSet', 'N/A')}°C)")
            
            _LOGGER.info("\n\033[92m✓ Tests terminés avec succès!\033[0m")

        except AuthenticationException as e:
            _LOGGER.error(f"\033[91m❌ Erreur d'authentification: {e.message}\033[0m")
            _LOGGER.debug(f"Status: {e.status}, Response: {e.response}")
        except Exception as e:
            _LOGGER.error(f"\033[91m❌ Une erreur inattendue est survenue: {e}\033[0m", exc_info=True)

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Script de test pour l'API Aldes.")
    parser.add_argument("username", help="Nom d'utilisateur (email) pour le compte Aldes.")
    parser.add_argument("password", help="Mot de passe du compte Aldes.")

    args = parser.parse_args()
    if not args.username or not args.password:
        _LOGGER.error("Le nom d'utilisateur et le mot de passe sont requis.")
        sys.exit(1)

    asyncio.run(test_api(args.username, args.password))

if __name__ == "__main__":
    main()
