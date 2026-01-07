"""Basic tests that don't require Home Assistant."""
from __future__ import annotations

from custom_components.gc_bad import const
from custom_components.gc_bad.config_flow import get_countries


def test_constants():
    """Test that constants are defined correctly."""
    print("\n\n=== Testing Constants ===")
    
    assert const.DOMAIN == "gc_bad"
    assert const.CONF_API_SECRET == "api_secret"
    assert const.API_BASE_URL == "https://bankaccountdata.gocardless.com"
    
    # Test rate limits
    assert const.RATE_LIMIT_BALANCES == 2
    assert const.RATE_LIMIT_DETAILS == 2
    assert const.RATE_LIMIT_TRANSACTIONS == 4
    
    print("[OK] All constants defined correctly")
    print(f"  Domain: {const.DOMAIN}")
    print(f"  API URL: {const.API_BASE_URL}")
    print(f"  Rate limits: B={const.RATE_LIMIT_BALANCES}, "
          f"D={const.RATE_LIMIT_DETAILS}, T={const.RATE_LIMIT_TRANSACTIONS}")


def test_get_countries():
    """Test that get_countries returns valid country data."""
    print("\n\n=== Testing Country Data ===")
    
    countries = get_countries()
    
    assert isinstance(countries, dict)
    assert len(countries) > 200
    
    # Test specific countries
    test_cases = {
        "US": "United States",
        "GB": "United Kingdom",
        "DE": "Germany",
        "FR": "France",
        "ES": "Spain",
        "IT": "Italy",
    }
    
    for code, name in test_cases.items():
        assert code in countries
        assert countries[code] == name
        print(f"  [OK] {code}: {name}")
    
    print(f"\n[OK] Total countries: {len(countries)}")


def test_manifest_structure():
    """Test that manifest.json exists and has required fields."""
    print("\n\n=== Testing Manifest ===")
    
    import json
    from pathlib import Path
    
    manifest_path = Path(__file__).parent.parent / "custom_components" / "gc_bad" / "manifest.json"
    assert manifest_path.exists(), "Manifest file not found"
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Required fields
    required_fields = [
        "domain",
        "name",
        "version",
        "config_flow",
        "requirements",
        "dependencies",
    ]
    
    for field in required_fields:
        assert field in manifest, f"Missing required field: {field}"
        print(f"  [OK] {field}: {manifest[field]}")
    
    assert manifest["domain"] == "gc_bad"
    assert manifest["config_flow"] is True
    
    print("\n[OK] Manifest structure is valid")


def test_integration_files_exist():
    """Test that all required integration files exist."""
    print("\n\n=== Testing File Structure ===")
    
    from pathlib import Path
    
    base_path = Path(__file__).parent.parent / "custom_components" / "gc_bad"
    
    required_files = [
        "__init__.py",
        "manifest.json",
        "const.py",
        "config_flow.py",
        "coordinator.py",
        "api_client.py",
        "sensor.py",
        "views.py",
        "translations/en.json",
    ]
    
    for file_name in required_files:
        file_path = base_path / file_name
        assert file_path.exists(), f"Missing file: {file_name}"
        print(f"  [OK] {file_name}")
    
    print("\n[OK] All required files present")

