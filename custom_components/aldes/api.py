"""Aldes API Client."""
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime, timedelta
import backoff
import aiohttp
from aiohttp import ClientError, ClientTimeout
from urllib.parse import urlencode

_LOGGER = logging.getLogger(__name__)


class AuthenticationException(Exception):
    """Authentication exception."""
    def __init__(self, message="Échec de l'authentification", status=None, response=None):
        self.message = message
        self.status = status
        self.response = response
        super().__init__(self.message)


class AuthResponse:
    """Réponse d'authentification."""
    def __init__(self, json_response: Dict[str, Any]):
        self.access_token = json_response.get("access_token")
        self.token_type = json_response.get("token_type")
        self.expires_in = json_response.get("expires_in")
        self.scope = json_response.get("scope")
        self.needUpdate = json_response.get("needUpdate")


class AldesApi:
    """Aldes API client."""

    _API_URL_TOKEN = "https://aldesiotsuite-aldeswebapi.azurewebsites.net/oauth2/token"
    _API_URL_PRODUCTS = "https://aldesiotsuite-aldeswebapi.azurewebsites.net/aldesoc/v5/users/me/products"
    _AUTHORIZATION_HEADER_KEY = "Authorization"
    _TOKEN_TYPE = "Bearer"
    _REQUEST_TIMEOUT = 30
    _MAX_RETRIES = 3

    def __init__(
        self, username: str, password: str, session: aiohttp.ClientSession
    ) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._session = session
        self._token = ""
        self._token_expires_at = datetime.now()
        self._timeout = ClientTimeout(total=self._REQUEST_TIMEOUT)
        self._cache = {}
        self._cache_timestamp = {}
        self._cache_ttl = timedelta(minutes=5)

    @backoff.on_exception(
        backoff.expo,
        (ClientError, asyncio.TimeoutError),
        max_tries=_MAX_RETRIES,
        max_time=60
    )
    async def authenticate(self) -> AuthResponse:
        """Get an access token with retry."""
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'User-Agent': 'AldesHomeAssistant/1.0'
        }

        # Données d'authentification simplifiées
        data = {
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
        }

        try:
            _LOGGER.debug("Tentative d'authentification à %s avec les données: %s",
                         self._API_URL_TOKEN,
                         {k: '***' if k == 'password' else v for k, v in data.items()})

            async with self._session.post(
                self._API_URL_TOKEN,
                data=data,  # Les données sont envoyées directement, aiohttp gère l'encodage
                headers=headers,
                timeout=self._timeout,
                ssl=True
            ) as response:
                response_text = await response.text()
                _LOGGER.debug("Réponse reçue (status: %s): %s", response.status, response_text)

                if response.status == 200:
                    try:
                        json_response = await response.json()
                        auth_response = AuthResponse(json_response)

                        self._token = auth_response.access_token
                        self._token_expires_at = datetime.now() + timedelta(seconds=auth_response.expires_in or 3600)

                        _LOGGER.debug("Authentification réussie, token valide pour %s secondes", auth_response.expires_in)

                        # Logging du message de mise à jour si présent
                        if auth_response.needUpdate:
                            _LOGGER.warning("Message de mise à jour disponible: %s",
                                          auth_response.needUpdate.get("message"))

                        return auth_response

                    except (KeyError, ValueError) as e:
                        raise AuthenticationException(f"Réponse invalide: {str(e)}", response.status, response_text)
                else:
                    error_details = ""
                    try:
                        error_json = await response.json()
                        error_details = f" - {error_json.get('error_description', '')}"
                    except:
                        pass

                    raise AuthenticationException(
                        f"Échec de l'authentification (status: {response.status}){error_details}",
                        response.status,
                        response_text
                    )

        except asyncio.TimeoutError as e:
            raise AuthenticationException(f"Timeout lors de l'authentification: {str(e)}")
        except ClientError as e:
            raise AuthenticationException(f"Erreur réseau lors de l'authentification: {str(e)}")
        except Exception as e:
            raise AuthenticationException(f"Erreur inattendue lors de l'authentification: {str(e)}")

    async def _get_cached_data(self, cache_key: str) -> Any:
        """Get cached data if valid."""
        if cache_key in self._cache:
            if datetime.now() - self._cache_timestamp[cache_key] < self._cache_ttl:
                _LOGGER.debug("Using cached data for %s", cache_key)
                return self._cache[cache_key]
        return None

    def _update_cache(self, cache_key: str, data: Any) -> None:
        """Update cache with new data."""
        self._cache[cache_key] = data
        self._cache_timestamp[cache_key] = datetime.now()

    @backoff.on_exception(
        backoff.expo,
        (ClientError, asyncio.TimeoutError),
        max_tries=_MAX_RETRIES,
        max_time=60
    )
    async def fetch_data(self) -> Dict:
        """Fetch data with cache and retry."""
        cache_key = "products"
        cached_data = await self._get_cached_data(cache_key)
        if cached_data:
            return cached_data

        try:
            async with await self._request_with_auth_interceptor(
                self._session.get,
                self._API_URL_PRODUCTS,
                timeout=self._timeout
            ) as response:
                data = await response.json()
                self._update_cache(cache_key, data)
                return data
        except Exception as e:
            _LOGGER.error("Error fetching data: %s", str(e))
            if cache_key in self._cache:
                _LOGGER.warning("Using stale cached data due to error")
                return self._cache[cache_key]
            raise

    @backoff.on_exception(
        backoff.expo,
        (ClientError, asyncio.TimeoutError),
        max_tries=_MAX_RETRIES,
        max_time=60
    )
    async def set_target_temperature(
        self, modem: str, thermostat_id: str, thermostat_name: str, target_temperature: float
    ) -> Dict:
        """Set target temperature with retry."""
        try:
            async with await self._request_with_auth_interceptor(
                self._session.patch,
                f"{self._API_URL_PRODUCTS}/{modem}/updateThermostats",
                json=[{
                    "ThermostatId": thermostat_id,
                    "Name": thermostat_name,
                    "TemperatureSet": int(target_temperature),
                }],
                timeout=self._timeout
            ) as response:
                return await response.json()
        except Exception as e:
            _LOGGER.error("Error setting temperature: %s", str(e))
            raise

    async def _request_with_auth_interceptor(self, request, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Enhanced request with auth retry."""
        if datetime.now() >= self._token_expires_at:
            await self.authenticate()

        try:
            response = await request(
                url,
                headers={self._AUTHORIZATION_HEADER_KEY: self._build_authorization()},
                **kwargs
            )
            if response.status == 401:
                await self.authenticate()
                response = await request(
                    url,
                    headers={self._AUTHORIZATION_HEADER_KEY: self._build_authorization()},
                    **kwargs
                )
            return response
        except Exception as e:
            _LOGGER.error("Request error: %s", str(e))
            raise

    def _build_authorization(self) -> str:
        """Build authorization header."""
        return f"{self._TOKEN_TYPE} {self._token}"
