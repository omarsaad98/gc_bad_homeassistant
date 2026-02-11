"""Basic tests for constants and file structure."""
from __future__ import annotations

import json
from pathlib import Path

from custom_components.gc_bad import const
from custom_components.gc_bad.config_flow import get_countries


def test_constants() -> None:
    """Test constants that define integration behavior."""
    assert const.DOMAIN == "gc_bad"
    assert const.CONF_SECRET_ID == "secret_id"
    assert const.CONF_SECRET_KEY == "secret_key"
    assert const.API_BASE_URL == "https://bankaccountdata.gocardless.com"
    assert const.RATE_LIMIT_BALANCES == 1
    assert const.RATE_LIMIT_DETAILS == 1
    assert const.RATE_LIMIT_TRANSACTIONS == 3


def test_get_countries() -> None:
    """Test country helper used by options flow."""
    countries = get_countries()
    assert isinstance(countries, dict)
    assert len(countries) > 200
    assert countries["US"] == "United States"
    assert countries["GB"] == "United Kingdom"


def test_manifest_structure() -> None:
    """Manifest must expose required integration metadata."""
    manifest_path = Path(__file__).parent.parent / "custom_components" / "gc_bad" / "manifest.json"
    with manifest_path.open(encoding="utf-8") as file:
        manifest = json.load(file)

    assert manifest["domain"] == "gc_bad"
    assert manifest["config_flow"] is True
    assert "version" in manifest
    assert "documentation" in manifest


def test_integration_files_exist() -> None:
    """Ensure key modules exist in the integration package."""
    base = Path(__file__).parent.parent / "custom_components" / "gc_bad"
    expected = [
        "__init__.py",
        "manifest.json",
        "const.py",
        "config_flow.py",
        "coordinator.py",
        "entity.py",
        "sensor.py",
        "storage.py",
        "models.py",
        "views.py",
        "api/client.py",
        "api/auth.py",
        "api/rate_limits.py",
        "translations/en.json",
    ]
    for relative in expected:
        assert (base / relative).exists(), f"Missing file: {relative}"

