"""Tests for config flow helpers."""
from __future__ import annotations

from custom_components.gc_bad.config_flow import GoCardlessConfigFlow, get_countries


def test_get_countries() -> None:
    """Country helper should provide common ISO country names."""
    countries = get_countries()
    assert "US" in countries
    assert countries["GB"] == "United Kingdom"

def test_config_flow_version() -> None:
    """Config flow version remains stable."""
    assert GoCardlessConfigFlow.VERSION == 1

