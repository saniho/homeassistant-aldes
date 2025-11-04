"""Tests for the Aldes API."""
import asyncio
import pytest
from unittest.mock import Mock, patch
from aiohttp import ClientSession, ClientError
from datetime import datetime, timedelta

from custom_components.aldes.api import AldesApi, AuthenticationException

@pytest.fixture
def api():
    """Create a test API instance."""
    session = Mock(spec=ClientSession)
    return AldesApi("test_user", "test_pass", session)

@pytest.mark.asyncio
async def test_authenticate_success(api):
    """Test successful authentication."""
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = asyncio.coroutine(lambda: {
        "access_token": "test_token",
        "expires_in": 3600
    })

    api._session.post = asyncio.coroutine(lambda *args, **kwargs: mock_response)

    await api.authenticate()
    assert api._token == "test_token"
    assert api._token_expires_at > datetime.now()

@pytest.mark.asyncio
async def test_authenticate_failure(api):
    """Test authentication failure."""
    mock_response = Mock()
    mock_response.status = 401

    api._session.post = asyncio.coroutine(lambda *args, **kwargs: mock_response)

    with pytest.raises(AuthenticationException):
        await api.authenticate()

@pytest.mark.asyncio
async def test_fetch_data_with_cache(api):
    """Test data fetching with cache."""
    # Premier appel - pas de cache
    mock_response = Mock()
    mock_response.status = 200
    test_data = {"test": "data"}
    mock_response.json = asyncio.coroutine(lambda: test_data)

    api._session.get = asyncio.coroutine(lambda *args, **kwargs: mock_response)
    api._token = "test_token"  # Simuler une authentification réussie

    result = await api.fetch_data()
    assert result == test_data

    # Deuxième appel - devrait utiliser le cache
    api._session.get = asyncio.coroutine(lambda *args, **kwargs: Mock())  # Cette mock ne devrait pas être appelée
    cached_result = await api.fetch_data()
    assert cached_result == test_data

@pytest.mark.asyncio
async def test_set_target_temperature(api):
    """Test setting target temperature."""
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = asyncio.coroutine(lambda: {"status": "success"})

    api._session.patch = asyncio.coroutine(lambda *args, **kwargs: mock_response)
    api._token = "test_token"

    result = await api.set_target_temperature("modem1", "thermo1", "Room1", 21)
    assert result == {"status": "success"}

@pytest.mark.asyncio
async def test_retry_on_network_error(api):
    """Test retry mechanism on network error."""
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:  # Échoue les 2 premières fois
            raise ClientError()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = asyncio.coroutine(lambda: {"test": "data"})
        return mock_response

    api._session.get = mock_request
    api._token = "test_token"

    result = await api.fetch_data()
    assert result == {"test": "data"}
    assert call_count == 3  # Vérifie que le retry a bien fonctionné
