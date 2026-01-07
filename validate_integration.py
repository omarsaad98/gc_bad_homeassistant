#!/usr/bin/env python3
"""Validation script for the GoCardless Home Assistant integration."""

import json
import sys
from pathlib import Path

# Set encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def validate_manifest():
    """Validate manifest.json structure."""
    manifest_path = Path("custom_components/gc_bad/manifest.json")
    
    if not manifest_path.exists():
        print("[FAIL] manifest.json not found!")
        return False
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    required_fields = ["domain", "name", "version", "config_flow", "requirements", "dependencies"]
    missing = [field for field in required_fields if field not in manifest]
    
    if missing:
        print(f"[FAIL] Missing required fields in manifest.json: {missing}")
        return False
    
    if manifest["domain"] != "gc_bad":
        print(f"[FAIL] Domain should be 'gc_bad', got '{manifest['domain']}'")
        return False
    
    if not manifest["config_flow"]:
        print("[FAIL] config_flow should be true")
        return False
    
    print("[OK] manifest.json is valid")
    return True


def validate_required_files():
    """Check all required integration files exist."""
    required_files = [
        "custom_components/gc_bad/__init__.py",
        "custom_components/gc_bad/manifest.json",
        "custom_components/gc_bad/config_flow.py",
        "custom_components/gc_bad/const.py",
        "custom_components/gc_bad/coordinator.py",
        "custom_components/gc_bad/api_client.py",
        "custom_components/gc_bad/sensor.py",
        "custom_components/gc_bad/views.py",
        "custom_components/gc_bad/translations/en.json",
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if not path.exists():
            print(f"[FAIL] Missing required file: {file_path}")
            all_exist = False
    
    if all_exist:
        print("[OK] All required files present")
    
    return all_exist


def validate_translations():
    """Validate translations file."""
    trans_path = Path("custom_components/gc_bad/translations/en.json")
    
    if not trans_path.exists():
        print("[FAIL] translations/en.json not found!")
        return False
    
    with open(trans_path) as f:
        translations = json.load(f)
    
    if "config" not in translations:
        print("[FAIL] 'config' section missing from translations")
        return False
    
    if "options" not in translations:
        print("[FAIL] 'options' section missing from translations")
        return False
    
    print("[OK] translations/en.json is valid")
    return True


def validate_imports():
    """Check if key modules can be imported."""
    try:
        import pycountry
        countries = list(pycountry.countries)
        print(f"[OK] pycountry working ({len(countries)} countries available)")
    except ImportError as e:
        print(f"[FAIL] Failed to import pycountry: {e}")
        return False
    
    try:
        import aiohttp
        print(f"[OK] aiohttp available (v{aiohttp.__version__})")
    except ImportError as e:
        print(f"[FAIL] Failed to import aiohttp: {e}")
        return False
    
    return True


def main():
    """Run all validations."""
    print("Validating GoCardless Home Assistant Integration\n")
    
    results = [
        validate_required_files(),
        validate_manifest(),
        validate_translations(),
        validate_imports(),
    ]
    
    print("\n" + "=" * 50)
    if all(results):
        print("All validations passed!")
        print("Integration is ready for testing")
        return 0
    else:
        print("Some validations failed")
        print("Please fix the issues above")
        return 1


if __name__ == "__main__":
    sys.exit(main())

