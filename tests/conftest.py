"""Test configuration and fixtures."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import pytest

from custom_components.gc_bad.const import CONF_SECRET_ID, CONF_SECRET_KEY, DOMAIN

# Load environment variables from .env file
load_dotenv()

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DATA_DIR.mkdir(exist_ok=True)

# Token file (will be gitignored)
TOKEN_FILE = TEST_DATA_DIR / "tokens.json"
API_RESPONSES_DIR = TEST_DATA_DIR / "api_responses"
API_RESPONSES_DIR.mkdir(exist_ok=True)


@pytest.fixture
def secret_id() -> str:
    """Get Secret ID from environment variable."""
    secret_id = os.getenv("GCD_SECRET_ID")
    if not secret_id:
        pytest.skip("GCD_SECRET_ID environment variable not set")
    return secret_id


@pytest.fixture
def secret_key() -> str:
    """Get Secret Key from environment variable."""
    secret_key = os.getenv("GCD_SECRET_KEY")
    if not secret_key:
        pytest.skip("GCD_SECRET_KEY environment variable not set")
    return secret_key


@pytest.fixture
def mock_config_entry(secret_id: str, secret_key: str):
    """Create a mock config entry."""
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import Mock
    
    entry = Mock(spec=ConfigEntry)
    entry.domain = DOMAIN
    entry.data = {
        CONF_SECRET_ID: secret_id,
        CONF_SECRET_KEY: secret_key,
    }
    entry.entry_id = "test_entry_id"
    return entry


def save_tokens(tokens: dict[str, Any]) -> None:
    """Save tokens to file with expiry information."""
    token_data = {
        "access_token": tokens.get("access"),
        "refresh_token": tokens.get("refresh"),
        "access_expires": tokens.get("access_expires"),
        "refresh_expires": tokens.get("refresh_expires"),
        "saved_at": datetime.now().isoformat(),
    }
    
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    
    print(f"\n✓ Tokens saved to {TOKEN_FILE}")
    print(f"  Access token expires: {token_data.get('access_expires', 'N/A')}")
    print(f"  Refresh token expires: {token_data.get('refresh_expires', 'N/A')}")


def load_tokens() -> dict[str, Any] | None:
    """Load saved tokens if they exist and are valid."""
    if not TOKEN_FILE.exists():
        return None
    
    with open(TOKEN_FILE) as f:
        token_data = json.load(f)
    
    # Check if access token is still valid
    if token_data.get("access_expires"):
        expiry = datetime.fromisoformat(token_data["access_expires"])
        if expiry > datetime.now():
            return token_data
    
    return None


def save_api_response(endpoint: str, response: dict[str, Any]) -> None:
    """Save API response to file for review."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean endpoint for filename
    clean_endpoint = endpoint.replace("/", "_").replace("?", "_").replace("=", "_")
    filename = f"{timestamp}_{clean_endpoint}.json"
    filepath = API_RESPONSES_DIR / filename
    
    with open(filepath, "w") as f:
        json.dump(response, f, indent=2)
    
    print(f"  [SAVED] Response saved to {filepath}")


@pytest.fixture
def response_logger():
    """Fixture to log API responses."""
    return save_api_response

