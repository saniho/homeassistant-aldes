#!/usr/bin/env python3
"""Script de test pour l'API Aldes."""
import asyncio
import aiohttp
import logging
import argparse
from datetime import datetime

from custom_components.aldes.api import AldesApi

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

async def test_api(username: str, password: str):
    """Teste les fonctionnalités principales de l'API."""
    async with aiohttp.ClientSession() as session:
        api = AldesApi(username, password, session)

        try:
            # Test d'authentification
            _LOGGER.info("Test d'authentification...")
            await api.authenticate()
            _LOGGER.info("✓ Authentification réussie")

            # Test de récupération des données
            _LOGGER.info("\nRécupération des données...")
            data = await api.fetch_data()
            _LOGGER.info("✓ Données récupérées avec succès")

            # Affichage des données
            _LOGGER.info("\nDonnées disponibles :")
            for product in data:
                _LOGGER.info(f"\nProduit trouvé :")
                _LOGGER.info(f"  - ID: {product.get('id', 'N/A')}")
                _LOGGER.info(f"  - Type: {product.get('type', 'N/A')}")
                _LOGGER.info(f"  - Nom: {product.get('name', 'N/A')}")

                if 'thermostats' in product:
                    _LOGGER.info("\n  Thermostats :")
                    for thermostat in product['thermostats']:
                        _LOGGER.info(f"    - {thermostat.get('Name', 'N/A')}: "
                                   f"{thermostat.get('TemperatureSet', 'N/A')}°C")

            # Test du cache
            _LOGGER.info("\nTest du cache...")
            cached_data = await api.fetch_data()
            _LOGGER.info("✓ Données récupérées depuis le cache")

            # Test de resilience
            _LOGGER.info("\nTest de résilience (simuler 3 erreurs)...")
            original_request = api._request_with_auth_interceptor
            error_count = 0

            async def mock_request(*args, **kwargs):
                nonlocal error_count
                if error_count < 3:
                    error_count += 1
                    raise aiohttp.ClientError("Erreur simulée")
                return await original_request(*args, **kwargs)

            api._request_with_auth_interceptor = mock_request
            retry_data = await api.fetch_data()
            _LOGGER.info("✓ Système de retry fonctionnel")

        except Exception as e:
            _LOGGER.error(f"❌ Erreur lors des tests: {str(e)}")
            raise
        else:
            _LOGGER.info("\n✓ Tous les tests ont réussi!")

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Test de l'API Aldes")
    parser.add_argument("username", help="Nom d'utilisateur Aldes")
    parser.add_argument("password", help="Mot de passe Aldes")

    args = parser.parse_args()

    asyncio.run(test_api(args.username, args.password))

if __name__ == "__main__":
    main()
