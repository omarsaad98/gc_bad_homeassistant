"""Reset rate limit counters in Home Assistant storage (for testing)."""
import json
from pathlib import Path

ha_storage = Path("C:/homeassistant/.storage")

# Find and update gc_bad storage files
for storage_file in ha_storage.glob("gc_bad_storage_*.json"):
    print(f"Found: {storage_file}")
    
    with open(storage_file) as f:
        data = json.load(f)
    
    if "data" in data and "rate_limits" in data["data"]:
        print(f"  Rate limits before: {len(data['data']['rate_limits'])} entries")
        data["data"]["rate_limits"] = {}
        print(f"  Rate limits after: CLEARED")
        
        with open(storage_file, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"  [OK] Reset rate limits in {storage_file.name}")
    else:
        print(f"  [INFO] No rate limits to clear")

print("\n[OK] Rate limit counters reset!")
print("[INFO] Reload the integration in Home Assistant to apply")

