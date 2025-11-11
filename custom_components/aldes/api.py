"""Aldes API Client."""
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime, timedelta, timezone
import backoff
import aiohttp
from aiohttp import ClientError, ClientTimeout
from urllib.parse import urlencode
import json

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


class AldesApi:
    """Aldes API client."""

    _API_URL_TOKEN = "https://aldesiotsuite-aldeswebapi.azurewebsites.net/oauth2/token"
    _API_URL_PRODUCTS = "https://aldesiotsuite-aldeswebapi.azurewebsites.net/aldesoc/v5/users/me/products"
    _AUTHORIZATION_HEADER_KEY = "Authorization"
    _API_KEY_HEADER = "apikey"
    _TOKEN_TYPE = "Bearer"
    _REQUEST_TIMEOUT = 30
    _MAX_RETRIES = 3
    _API_KEY = "XQibgk1ozo1wjVQcvcoFQqMl3pjEwcRv"  # API key fixe

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
        self._user_agent = "AldesConnect/2.0.0"

    def _log_request_details(self, method: str, url: str, headers: Dict, data: Any = None) -> None:
        """Log request details for debugging."""
        _LOGGER.debug("=== Détails de la requête ===")
        _LOGGER.debug("Méthode: %s", method)
        _LOGGER.debug("URL: %s", url)
        _LOGGER.debug("Headers: %s", {k: v for k, v in headers.items() if k.lower() != 'authorization'})
        if data:
            safe_data = data
            if isinstance(data, dict) and 'password' in data:
                safe_data = data.copy()
                safe_data['password'] = '***'
            _LOGGER.debug("Data: %s", safe_data)

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
            'User-Agent': self._user_agent,
            self._API_KEY_HEADER: self._API_KEY
        }

        data = {
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
            "scope": "openid profile email offline_access"
        }

        self._log_request_details("POST", self._API_URL_TOKEN, headers, data)

        try:
            async with self._session.post(
                self._API_URL_TOKEN,
                data=data,
                headers=headers,
                timeout=self._timeout,
                ssl=True
            ) as response:
                response_text = await response.text()
                _LOGGER.debug("=== Détails de la réponse ===")
                _LOGGER.debug("Status: %s", response.status)
                _LOGGER.debug("Headers: %s", dict(response.headers))
                _LOGGER.debug("Body: %s", response_text)

                if response.status == 200:
                    try:
                        json_response = await response.json()
                        auth_response = AuthResponse(json_response)
                        self._token = auth_response.access_token
                        self._token_expires_at = datetime.now() + timedelta(seconds=auth_response.expires_in or 3600)
                        _LOGGER.info("Authentification réussie")
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

        except Exception as e:
            _LOGGER.error("Erreur lors de l'authentification: %s", str(e))
            raise

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
        url = f"{self._API_URL_PRODUCTS}/{modem}/updateThermostats"
        payload = [{
            "ThermostatId": thermostat_id,
            "Name": thermostat_name,
            "TemperatureSet": int(target_temperature),
        }]
        
        self._log_request_details("PATCH", url, {}, payload)
        
        try:
            async with await self._request_with_auth_interceptor(
                self._session.patch,
                url,
                json=payload,
                timeout=self._timeout
            ) as response:
                response.raise_for_status()
                if 'application/json' in response.headers.get('Content-Type', ''):
                    return await response.json()
                return {} # Return empty dict if no JSON content is expected or found
        except Exception as e:
            _LOGGER.error("Error setting temperature: %s", str(e))
            raise

    @backoff.on_exception(
        backoff.expo,
        (ClientError, asyncio.TimeoutError),
        max_tries=_MAX_RETRIES,
        max_time=60
    )
    async def change_mode(self, modem: str, mode: str) -> Dict:
        """Send a command to change the mode."""
        url = f"{self._API_URL_PRODUCTS}/{modem}/command"
        payload = {"command": mode}
        
        self._log_request_details("POST", url, {}, payload)

        try:
            async with await self._request_with_auth_interceptor(
                self._session.post,
                url,
                json=payload,
                timeout=self._timeout
            ) as response:
                response.raise_for_status()
                if 'application/json' in response.headers.get('Content-Type', ''):
                    return await response.json()
                return {} # Return empty dict if no JSON content is expected or found
        except Exception as e:
            _LOGGER.error("Error changing mode: %s", str(e))
            raise

    @backoff.on_exception(
        backoff.expo,
        (ClientError, asyncio.TimeoutError),
        max_tries=_MAX_RETRIES,
        max_time=60
    )
    async def set_vacation_mode(self, modem: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict:
        """Set or unset vacation mode by sending a 'W' command."""
        url = f"{self._API_URL_PRODUCTS}/{modem}/commands"
        
        if start_date and end_date:
            # Ensure dates are in UTC before formatting
            start_utc = start_date.astimezone(timezone.utc)
            end_utc = end_date.astimezone(timezone.utc)
            
            # Format dates to YYYYMMDDHHMMSS
            start_str = start_utc.strftime("%Y%m%d%H%M%S")
            end_str = end_utc.strftime("%Y%m%d%H%M%S")
            command = f"W{start_str}Z{end_str}Z"
        else:
            # To disable, send a vacation command for a time in the past
            past_date = datetime.now(timezone.utc) - timedelta(days=1)
            past_str = past_date.strftime("%Y%m%d%H%M%S")
            command = f"W{past_str}Z{past_str}Z"

        #payload = {"command": command}
        payload = {
          "method": "changeMode",
          "params": [command]
        }
        self._log_request_details("POST", url, {}, payload)
        #print(payload)
        #print( 1/0)
        try:
            async with await self._request_with_auth_interceptor(
                self._session.post,
                url,
                json=payload,
                timeout=self._timeout
            ) as response:
                response.raise_for_status()
                if 'application/json' in response.headers.get('Content-Type', ''):
                    return await response.json()
                return {}
        except Exception as e:
            _LOGGER.error("Error setting vacation mode: %s", str(e))
            raise

    @backoff.on_exception(
        backoff.expo,
        (ClientError, asyncio.TimeoutError),
        max_tries=_MAX_RETRIES,
        max_time=60
    )
    async def set_frost_protection(self, modem: str, enabled: bool) -> Dict:
        """Set or unset frost protection mode."""
        url = f"{self._API_URL_PRODUCTS}/{modem}"
        payload = {
            "indicator": {
                "hors_gel": enabled,
            }
        }
        
        self._log_request_details("PATCH", url, {}, payload)

        try:
            async with await self._request_with_auth_interceptor(
                self._session.patch,
                url,
                json=payload,
                timeout=self._timeout
            ) as response:
                response.raise_for_status()
                if 'application/json' in response.headers.get('Content-Type', ''):
                    return await response.json()
                return {} # Return empty dict if no JSON content is expected or found
        except Exception as e:
            _LOGGER.error("Error setting frost protection: %s", str(e))
            raise

    async def _request_with_auth_interceptor(self, request, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Enhanced request with auth retry."""
        if datetime.now() >= self._token_expires_at:
            await self.authenticate()

        try:
            headers = {
                self._AUTHORIZATION_HEADER_KEY: self._build_authorization(),
                self._API_KEY_HEADER: self._API_KEY  # Ajout de l'API key dans tous les appels
            }
            if 'headers' in kwargs:
                headers.update(kwargs['headers'])
            kwargs['headers'] = headers

            response = await request(url, **kwargs)

            if response.status == 401:
                await self.authenticate()
                response = await request(url, **kwargs)
            return response
        except Exception as e:
            _LOGGER.error("Request error: %s", str(e))
            raise

    def _build_authorization(self) -> str:
        """Build authorization header."""
        return f"{self._TOKEN_TYPE} {self._token}"
