#!/usr/bin/env python3
"""Script de test pour le changement de mode vacances de l'API Aldes."""
import asyncio
import aiohttp
import logging
import argparse
import os
import sys
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from custom_components.aldes.api import AldesApi, AuthenticationException

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_LOGGER = logging.getLogger(__name__)

async def test_vacation_command(username: str, password: str, start_date_str: str | None, end_date_str: str | None, disable: bool):
    """Teste l'envoi de la commande de mode vacances."""
    _LOGGER.info("Démarrage du test de la commande vacances")

    async with aiohttp.ClientSession() as session:
        api = AldesApi(username, password, session)

        try:
            # 1. Fetch data to get the modem ID (authentication is automatic)
            _LOGGER.info("Récupération des données pour trouver l'ID de l'appareil...")
            products = await api.fetch_data()
            if not products:
                _LOGGER.error("Aucun produit trouvé pour ce compte.")
                return

            # Assume we are controlling the first product found
            modem_id = products[0].get("modem")
            if not modem_id or modem_id == "N/A":
                _LOGGER.error(f"ID de modem invalide trouvé: {modem_id}")
                return
            
            _LOGGER.info(f"Appareil trouvé avec l'ID: {modem_id}")

            # 2. Prepare and send the command
            if disable:
                _LOGGER.info("Envoi de la commande pour DÉSACTIVER le mode vacances...")
                await api.set_away_mode(modem_id, enabled=False)
            elif start_date_str and end_date_str:
                _LOGGER.info(f"Envoi de la commande pour ACTIVER le mode vacances du {start_date_str} au {end_date_str}...")
                try:
                    start_date_dt = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
                    end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
                    await api.set_away_mode(modem_id, enabled=True, start_date=start_date_dt, end_date=end_date_dt)
                except ValueError:
                    _LOGGER.error("Format de date invalide. Utilisez 'YYYY-MM-DD HH:MM:SS'.")
                    return
            else:
                _LOGGER.error("Vous devez soit utiliser --disable, soit fournir --start et --end.")
                return

            _LOGGER.info("\033[92m✓ Commande envoyée avec succès !\033[0m")
            _LOGGER.info("Veuillez vérifier l'état de votre appareil ou relancer test_api.py après quelques instants pour voir le changement.")

        except AuthenticationException as e:
            _LOGGER.error(f"\033[91m❌ Erreur d'authentification: {e.message}\033[0m")
        except Exception as e:
            _LOGGER.error(f"\033[91m❌ Une erreur est survenue: {e}\033[0m", exc_info=True)

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Test de la commande de mode vacances Aldes.")
    parser.add_argument("username", help="Nom d'utilisateur Aldes")
    parser.add_argument("password", help="Mot de passe Aldes")
    parser.add_argument("--start", help="Date de début des vacances au format 'YYYY-MM-DD HH:MM:SS'")
    parser.add_argument("--end", help="Date de fin des vacances au format 'YYYY-MM-DD HH:MM:SS'")
    parser.add_argument("--disable", action="store_true", help="Désactive le mode vacances")

    args = parser.parse_args()

    asyncio.run(test_vacation_command(args.username, args.password, args.start, args.end, args.disable))

if __name__ == "__main__":
    main()
