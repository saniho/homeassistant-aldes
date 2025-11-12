"""Tests for the Aldes API."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, Mock
from aiohttp import ClientSession, ClientError
from datetime import datetime, timedelta, timezone

from custom_components.aldes.api import AldesApi, AuthenticationException

# Helper to create a mock response that can be used in an `async with` block
def create_mock_response(status, json_data=None, text_data="", headers=None):
    """Create a mock aiohttp response."""
    mock_response = AsyncMock()
    mock_response.status = status
    
    final_headers = headers if headers is not None else {}

    if json_data:
        mock_response.json.return_value = json_data
        mock_response.text.return_value = str(json_data)
        if 'Content-Type' not in final_headers:
             final_headers['Content-Type'] = 'application/json'
    else:
        mock_response.text.return_value = text_data
    
    mock_response.headers = final_headers
    
    # Mock raise_for_status which is a sync method
    mock_response.raise_for_status = Mock()
    if status >= 400:
        mock_response.raise_for_status.side_effect = ClientError(f"HTTP Error {status}")

    # For `async with` statement
    mock_response.__aenter__.return_value = mock_response
    mock_response.__aexit__.return_value = None
    
    return mock_response

@pytest.fixture
def api():
    """Create a test API instance with a mocked session."""
    session = AsyncMock(spec=ClientSession)
    return AldesApi("test_user", "test_pass", session)

# This helper mocks the _request_with_auth_interceptor to simplify testing methods that use it.
def mock_interceptor(api, response):
    """Mock the auth interceptor."""
    api._request_with_auth_interceptor = AsyncMock(return_value=response)

@pytest.mark.asyncio
async def test_authenticate_success(api):
    """Test successful authentication."""
    mock_response = create_mock_response(200, {
        "access_token": "test_token",
        "expires_in": 3600
    })
    api._session.post.return_value = mock_response

    await api.authenticate()
    assert api._token == "test_token"
    assert api._token_expires_at > datetime.now()

@pytest.mark.asyncio
async def test_authenticate_failure(api):
    """Test authentication failure."""
    mock_response = create_mock_response(401, {"error": "invalid_grant"}, '{"error": "invalid_grant"}')
    api._session.post.return_value = mock_response

    with pytest.raises(AuthenticationException):
        await api.authenticate()

@pytest.mark.asyncio
async def test_fetch_data_with_cache(api):
    """Test data fetching with cache."""
    test_data = {"test": "data"}
    mock_response = create_mock_response(200, test_data)
    mock_interceptor(api, mock_response)
    api._token = "test_token"
    api._token_expires_at = datetime.now() + timedelta(hours=1)

    # First call - should call the API
    result = await api.fetch_data()
    assert result == test_data
    api._request_with_auth_interceptor.assert_called_once()

    # Second call - should use cache
    api._request_with_auth_interceptor.reset_mock()
    cached_result = await api.fetch_data()
    assert cached_result == test_data
    api._request_with_auth_interceptor.assert_not_called()

@pytest.mark.asyncio
async def test_set_target_temperature(api):
    """Test setting target temperature."""
    mock_response = create_mock_response(200, {"status": "success"})
    mock_interceptor(api, mock_response)
    api._token = "test_token"
    api._token_expires_at = datetime.now() + timedelta(hours=1)

    result = await api.set_target_temperature("modem1", "thermo1", "Room1", 21)
    assert result == {"status": "success"}
    
    args, kwargs = api._request_with_auth_interceptor.call_args
    assert args[0] == api._session.patch
    assert args[1] == f"{api._API_URL_PRODUCTS}/modem1/updateThermostats"
    assert kwargs['json'] == [{
        "ThermostatId": "thermo1",
        "Name": "Room1",
        "TemperatureSet": 21,
    }]

@pytest.mark.asyncio
async def test_change_mode(api):
    """Test changing mode."""
    mock_response = create_mock_response(200, {"status": "success"})
    mock_interceptor(api, mock_response)
    api._token = "test_token"
    api._token_expires_at = datetime.now() + timedelta(hours=1)

    result = await api.change_mode("modem1", "BOOST")
    assert result == {"status": "success"}

    args, kwargs = api._request_with_auth_interceptor.call_args
    assert args[0] == api._session.post
    assert args[1] == f"{api._API_URL_PRODUCTS}/modem1/commands"
    assert kwargs['json'] == {"command": "BOOST"}

@pytest.mark.asyncio
async def test_set_vacation_mode_on(api):
    """Test setting vacation mode on."""
    mock_response = create_mock_response(200, {"status": "success"})
    mock_interceptor(api, mock_response)
    api._token = "test_token"
    api._token_expires_at = datetime.now() + timedelta(hours=1)

    start_date = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end_date = datetime(2023, 1, 10, 18, 0, 0, tzinfo=timezone.utc)

    result = await api.set_vacation_mode("modem1", start_date, end_date)
    assert result == {"status": "success"}
    
    args, kwargs = api._request_with_auth_interceptor.call_args
    assert args[0] == api._session.post
    assert args[1] == f"{api._API_URL_PRODUCTS}/modem1/commands"
    expected_command = "W20230101100000Z20230110180000Z"
    assert kwargs['json'] == {"method": "changeMode", "params": [expected_command]}

@pytest.mark.asyncio
async def test_set_vacation_mode_off(api):
    """Test setting vacation mode off."""
    mock_response = create_mock_response(200, {"status": "success"})
    mock_interceptor(api, mock_response)
    api._token = "test_token"
    api._token_expires_at = datetime.now() + timedelta(hours=1)

    result = await api.set_vacation_mode("modem1", None, None)
    assert result == {"status": "success"}
    
    args, kwargs = api._request_with_auth_interceptor.call_args
    assert args[0] == api._session.post
    assert args[1] == f"{api._API_URL_PRODUCTS}/modem1/commands"
    expected_command = "W00010101000000Z00010101000000Z"
    assert kwargs['json'] == {"method": "changeMode", "params": [expected_command]}

@pytest.mark.asyncio
async def test_set_frost_protection_on(api):
    """Test setting frost protection mode on."""
    mock_response = create_mock_response(200, {"status": "success"})
    mock_interceptor(api, mock_response)
    api._token = "test_token"
    api._token_expires_at = datetime.now() + timedelta(hours=1)

    with patch('custom_components.aldes.api.datetime') as mock_dt:
        now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        
        result = await api.set_frost_protection("modem1", True)
        assert result == {"status": "success"}
        
        args, kwargs = api._request_with_auth_interceptor.call_args
        assert args[0] == api._session.post
        assert args[1] == f"{api._API_URL_PRODUCTS}/modem1/commands"
        expected_command = f"W{now.strftime('%Y%m%d%H%M%S')}Z00000000000000Z"
        assert kwargs['json'] == {"method": "changeMode", "params": [expected_command]}

@pytest.mark.asyncio
async def test_set_frost_protection_off(api):
    """Test setting frost protection mode off."""
    mock_response = create_mock_response(200, {"status": "success"})
    mock_interceptor(api, mock_response)
    api._token = "test_token"
    api._token_expires_at = datetime.now() + timedelta(hours=1)

    result = await api.set_frost_protection("modem1", False)
    assert result == {"status": "success"}
    
    args, kwargs = api._request_with_auth_interceptor.call_args
    assert args[0] == api._session.post
    assert args[1] == f"{api._API_URL_PRODUCTS}/modem1/commands"
    expected_command = "W00010101000000Z00010101000000Z"
    assert kwargs['json'] == {"method": "changeMode", "params": [expected_command]}

@pytest.mark.asyncio
async def test_fetch_data_retry(api):
    """Test retry mechanism on fetch_data."""
    api._token = "test_token"
    api._token_expires_at = datetime.now() + timedelta(hours=1)

    mock_interceptor = AsyncMock()
    mock_interceptor.side_effect = [
        ClientError("Attempt 1"),
        ClientError("Attempt 2"),
        create_mock_response(200, {"test": "data"})
    ]
    api._request_with_auth_interceptor = mock_interceptor

    result = await api.fetch_data()
    assert result == {"test": "data"}
    assert api._request_with_auth_interceptor.call_count == 3
