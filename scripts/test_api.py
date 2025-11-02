#!/usr/bin/env python3
"""Script de test pour l'API Aldes."""
import asyncio
import aiohttp
import logging
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)

def setup_import_path():
    """Configure le PYTHONPATH pour l'importation des modules."""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    _LOGGER.debug(f"Ajout du chemin au PYTHONPATH: {project_root}")
    sys.path.insert(0, str(project_root))

try:
    setup_import_path()
    from custom_components.aldes.api import AldesApi, AuthenticationException
except ImportError as e:
    _LOGGER.error(f"Erreur d'importation: {e}")
    _LOGGER.debug(f"PYTHONPATH actuel: {sys.path}")
    _LOGGER.debug(f"Répertoire courant: {os.getcwd()}")
    sys.exit(1)

async def test_api(username: str, password: str):
    """Teste les fonctionnalités principales de l'API."""
    _LOGGER.info("Démarrage des tests de l'API Aldes")
    _LOGGER.debug(f"Test avec l'utilisateur: {username}")

    # Configuration du client HTTP avec des headers personnalisés
    timeout = aiohttp.ClientTimeout(total=30)
    headers = {
        'User-Agent': 'AldesHomeAssistant/1.0',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        api = AldesApi(username, password, session)

        try:
            _LOGGER.info("Test d'authentification...")
            _LOGGER.debug("Tentative d'authentification à l'API Aldes...")

            try:
                auth_response = await api.authenticate()
                _LOGGER.info("✓ Authentification réussie")

                # Vérification du message de mise à jour
                if hasattr(auth_response, 'needUpdate') and auth_response.needUpdate:
                    update_info = auth_response.needUpdate
                    _LOGGER.warning("\nMessage de mise à jour détecté:")
                    _LOGGER.warning(f"  Message: {update_info.get('message', 'N/A')}")
                    _LOGGER.warning(f"  Store Android: {update_info.get('storeAndroid', 'N/A')}")
                    _LOGGER.warning(f"  Store Apple: {update_info.get('storeApple', 'N/A')}")

            except AuthenticationException as auth_err:
                _LOGGER.error("❌ Échec de l'authentification")
                _LOGGER.debug(f"Détails de l'erreur d'authentification: {auth_err}")
                return
            except Exception as e:
                _LOGGER.error(f"❌ Erreur inattendue lors de l'authentification: {e}")
                _LOGGER.debug(f"Type d'erreur: {type(e)}")
                return

            _LOGGER.info("Récupération des données...")
            try:
                data = await api.fetch_data()
                _LOGGER.debug(f"Données brutes reçues: {data}")

                if not data:
                    _LOGGER.warning("Aucune donnée n'a été récupérée")
                    return

                if not isinstance(data, list):
                    _LOGGER.info("Conversion des données en liste")
                    data = [data] if data else []

                _LOGGER.info(f"✓ Données récupérées: {len(data)} produits trouvés")

                for product in data:
                    if not isinstance(product, dict):
                        _LOGGER.warning(f"Produit invalide ignoré: {product}")
                        continue

                    _LOGGER.info("\nDétails du produit:")
                    _LOGGER.info(f"  ID: {product.get('modem', 'N/A')}")
                    _LOGGER.info(f"  Type: {product.get('type', 'N/A')}")
                    _LOGGER.info(f"  Nom: {product.get('name', 'N/A')}")
                    _LOGGER.info(f"  Référence: {product.get('reference', 'N/A')}")
                    _LOGGER.info(f"  Numéro de série: {product.get('serial_number', 'N/A')}")
                    _LOGGER.info(f"  Connecté: {product.get('isConnected', False)}")

                    # Accès aux données de l'indicateur
                    indicator = product.get('indicator', {})
                    if indicator:
                        _LOGGER.info("\n  Informations générales:")
                        _LOGGER.info(f"    Mode air actuel: {indicator.get('current_air_mode', 'N/A')}")
                        _LOGGER.info(f"    Mode eau actuel: {indicator.get('current_water_mode', 'N/A')}")
                        _LOGGER.info(f"    Température principale: {indicator.get('tmp_principal', 'N/A')}°C")
                        _LOGGER.info(f"    Quantité d'eau chaude: {indicator.get('qte_eau_chaude', 'N/A')}%")

                        # Lecture des thermostats depuis l'indicateur
                        thermostats = indicator.get('thermostats', [])
                        if thermostats:
                            _LOGGER.info("\n  Thermostats:")
                            for thermostat in thermostats:
                                name = thermostat.get('Name', '').strip() or f"Thermostat {thermostat.get('Number', 'N/A')}"
                                _LOGGER.info(f"    - {name}:")
                                _LOGGER.info(f"      ID: {thermostat.get('ThermostatId', 'N/A')}")
                                _LOGGER.info(f"      Température actuelle: {thermostat.get('CurrentTemperature', 'N/A')}°C")
                                _LOGGER.info(f"      Température de consigne: {thermostat.get('TemperatureSet', 'N/A')}°C")
                        else:
                            _LOGGER.info("  Aucun thermostat trouvé dans l'indicateur")
                    else:
                        _LOGGER.info("  Aucune donnée d'indicateur trouvée")

            except Exception as e:
                _LOGGER.error(f"Erreur lors de la récupération des données: {e}")
                _LOGGER.debug(f"Type d'erreur: {type(e)}")
                _LOGGER.debug(f"Détails de l'erreur: {str(e)}")
                return

        except aiohttp.ClientError as e:
            _LOGGER.error(f"Erreur réseau: {e}")
            _LOGGER.debug(f"Détails de l'erreur réseau: {str(e)}")
            raise
        except Exception as e:
            _LOGGER.error(f"Erreur inattendue: {e}")
            _LOGGER.debug(f"Type d'erreur: {type(e)}")
            raise
        else:
            _LOGGER.info("\n✓ Tests terminés avec succès!")

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Test de l'API Aldes")
    parser.add_argument("username", help="Nom d'utilisateur Aldes")
    parser.add_argument("password", help="Mot de passe Aldes")

    args = parser.parse_args()

    try:
        asyncio.run(test_api(args.username, args.password))
    except KeyboardInterrupt:
        _LOGGER.info("\nTests interrompus par l'utilisateur")
    except Exception as e:
        _LOGGER.error(f"Erreur lors de l'exécution des tests: {e}")
        _LOGGER.debug(f"Type d'erreur: {type(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
