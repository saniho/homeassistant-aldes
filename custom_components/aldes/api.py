"""Aldes API Client."""
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime, timedelta, timezone
import backoff
import aiohttp
from aiohttp import ClientError, ClientTimeout

_LOGGER = logging.getLogger(__name__)

# Constants
API_URL_BASE = "https://aldesiotsuite-aldeswebapi.azurewebsites.net"
API_URL_TOKEN = f"{API_URL_BASE}/oauth2/token"
API_URL_PRODUCTS = f"{API_URL_BASE}/aldesoc/v5/users/me/products"

HEADER_API_KEY = "apikey"
HEADER_AUTH = "Authorization"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_ACCEPT = "Accept"
HEADER_USER_AGENT = "User-Agent"

# Command constants
CMD_METHOD = "method"
CMD_PARAMS = "params"
CMD_COMMAND = "command"
CMD_CHANGE_MODE = "changeMode"
DISABLE_AWAY_COMMAND = "W00010101000000Z00010101000000Z"


class AuthenticationException(Exception):
    """Authentication exception."""
    def __init__(self, message="Échec de l'authentification", status=None, response=None):
        self.message = message
        self.status = status
        self.response = response
        super().__init__(self.message)


class AuthResponse:
    """Authentication response."""
    def __init__(self, json_response: Dict[str, Any]):
        self.access_token = json_response.get("access_token")
        self.token_type = json_response.get("token_type")
        self.expires_in = json_response.get("expires_in")
        self.scope = json_response.get("scope")


class AldesApi:
    """Aldes API client."""

    _API_KEY = "XQibgk1ozo1wjVQcvcoFQqMl3pjEwcRv"
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
        self._token: Optional[str] = None
        self._token_expires_at = datetime.now(timezone.utc)
        self._timeout = ClientTimeout(total=self._REQUEST_TIMEOUT)
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._user_agent = "AldesConnect/2.0.0"

    def _log_request_details(self, method: str, url: str, headers: Dict, data: Any = None) -> None:
        """Log request details for debugging."""
        _LOGGER.debug("=== Request Details ===")
        _LOGGER.debug("Method: %s", method)
        _LOGGER.debug("URL: %s", url)
        _LOGGER.debug("Headers: %s", {k: v for k, v in headers.items() if k.lower() != 'authorization'})
        if data:
            safe_data = data
            if isinstance(data, dict) and 'password' in data:
                safe_data = data.copy()
                safe_data['password'] = '***'
            _LOGGER.debug("Data: %s", safe_data)

    @backoff.on_exception(
        backoff.expo, (ClientError, asyncio.TimeoutError), max_tries=_MAX_RETRIES, max_time=60
    )
    async def authenticate(self) -> AuthResponse:
        """Get an access token with retry."""
        headers = {
            HEADER_CONTENT_TYPE: 'application/x-www-form-urlencoded',
            HEADER_ACCEPT: 'application/json',
            HEADER_USER_AGENT: self._user_agent,
            HEADER_API_KEY: self._API_KEY
        }
        data = {
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
            "scope": "openid profile email offline_access"
        }
        self._log_request_details("POST", API_URL_TOKEN, headers, data)

        try:
            async with self._session.post(
                API_URL_TOKEN, data=data, headers=headers, timeout=self._timeout, ssl=True
            ) as response:
                if response.status == 200:
                    json_response = await response.json()
                    auth_response = AuthResponse(json_response)
                    self._token = auth_response.access_token
                    self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=auth_response.expires_in or 3600)
                    _LOGGER.info("Authentication successful")
                    return auth_response
                
                response_text = await response.text()
                raise AuthenticationException(f"Authentication failed (status: {response.status})", response.status, response_text)
        except (ClientError, asyncio.TimeoutError, KeyError, ValueError) as e:
            _LOGGER.error("Error during authentication: %s", e)
            raise AuthenticationException(f"Authentication process failed: {e}") from e

    async def _get_cached_data(self, cache_key: str) -> Any:
        """Get cached data if valid."""
        if cache_key in self._cache and datetime.now(timezone.utc) - self._cache_timestamp[cache_key] < self._cache_ttl:
            _LOGGER.debug("Using cached data for %s", cache_key)
            return self._cache[cache_key]
        return None

    def _update_cache(self, cache_key: str, data: Any) -> None:
        """Update cache with new data."""
        self._cache[cache_key] = data
        self._cache_timestamp[cache_key] = datetime.now(timezone.utc)

    async def _request_with_auth_interceptor(self, request_func, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Execute a request, handling token expiration and renewal."""
        if datetime.now(timezone.utc) >= self._token_expires_at:
            await self.authenticate()

        kwargs['headers'] = kwargs.get('headers', {})
        kwargs['headers'][HEADER_AUTH] = self._build_authorization()
        kwargs['headers'][HEADER_API_KEY] = self._API_KEY

        response = await request_func(url, **kwargs)

        if response.status == 401:
            _LOGGER.info("Token expired or invalid, re-authenticating.")
            await self.authenticate()
            kwargs['headers'][HEADER_AUTH] = self._build_authorization()
            response = await request_func(url, **kwargs)
        
        return response

    async def _api_request(self, method: str, url: str, **kwargs) -> Dict:
        """Centralized method for making API requests with retry and error handling."""
        @backoff.on_exception(
            backoff.expo, (ClientError, asyncio.TimeoutError, AuthenticationException), 
            max_tries=self._MAX_RETRIES, max_time=60
        )
        async def _make_request():
            self._log_request_details(method.upper(), url, kwargs.get("headers", {}), kwargs.get("json"))
            request_func = getattr(self._session, method)
            try:
                async with await self._request_with_auth_interceptor(
                    request_func, url, **kwargs, timeout=self._timeout
                ) as response:
                    response.raise_for_status()
                    if 'application/json' in response.headers.get(HEADER_CONTENT_TYPE, ''):
                        return await response.json()
                    return {}
            except Exception as e:
                _LOGGER.error("Error during API request to %s: %s", url, e)
                raise
        return await _make_request()

    async def fetch_data(self) -> Dict:
        """Fetch data with cache and retry."""
        cache_key = "products"
        if cached_data := await self._get_cached_data(cache_key):
            return cached_data

        try:
            data = await self._api_request("get", API_URL_PRODUCTS)
            self._update_cache(cache_key, data)
            return data
        except Exception as e:
            _LOGGER.error("Failed to fetch data after retries: %s", e)
            if cache_key in self._cache:
                _LOGGER.warning("Using stale cached data due to error.")
                return self._cache[cache_key]
            raise

    async def set_target_temperature(
        self, modem: str, thermostat_id: str, thermostat_name: str, target_temperature: float
    ) -> Dict:
        """Set target temperature."""
        url = f"{API_URL_PRODUCTS}/{modem}/updateThermostats"
        payload = [{"ThermostatId": thermostat_id, "Name": thermostat_name, "TemperatureSet": int(target_temperature)}]
        return await self._api_request("patch", url, json=payload)

    async def change_mode(self, modem: str, mode: str) -> Dict:
        """Send a command to change the mode."""
        url = f"{API_URL_PRODUCTS}/{modem}/commands"
        payload = {CMD_COMMAND: mode}
        return await self._api_request("post", url, json=payload)

    async def set_away_mode(self, modem: str, enabled: bool, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict:
        """Set or unset away (vacation or frost-protection) mode."""
        url = f"{API_URL_PRODUCTS}/{modem}/commands"
        
        if enabled:
            start = start_date or datetime.now(timezone.utc)
            start_str = start.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
            
            if end_date:  # Vacation mode with end date
                end_str = end_date.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
            else:  # Frost-protection mode (no end date)
                end_str = "00000000000000"
            
            command = f"W{start_str}Z{end_str}Z"
        else:  # Disable
            command = DISABLE_AWAY_COMMAND

        payload = {CMD_METHOD: CMD_CHANGE_MODE, CMD_PARAMS: [command]}
        #print(payload)
        #print(1/0)
        await self._api_request("post", url, json=payload)

    def _build_authorization(self) -> str:
        """Build authorization header."""
        return f"{self._TOKEN_TYPE} {self._token}"
