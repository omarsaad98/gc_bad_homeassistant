"""Constants for the GoCardless Bank Account Data integration."""
from datetime import timedelta

DOMAIN = "gc_bad"
CONF_SECRET_ID = "secret_id"
CONF_SECRET_KEY = "secret_key"

# API endpoints
API_BASE_URL = "https://bankaccountdata.gocardless.com"

# Rate limits (per day per account/scope), intentionally conservative.
RATE_LIMIT_BALANCES = 1
RATE_LIMIT_DETAILS = 1
RATE_LIMIT_TRANSACTIONS = 3

# Update intervals based on rate limits with buffer
UPDATE_INTERVAL_BALANCES = timedelta(hours=24)  # Once per day (safe with 1/day limit)
UPDATE_INTERVAL_DETAILS = timedelta(hours=24)   # Once per day (safe with 1/day limit)
UPDATE_INTERVAL_TRANSACTIONS = timedelta(hours=8)  # 3 times per day
UPDATE_INTERVAL_REQUISITIONS = timedelta(minutes=30)  # More frequent for list updates

# Scheduled refresh behavior (local time)
SCHEDULED_REFRESH_HOURS = (6, 18)
REFRESH_SKIP_WINDOW = timedelta(hours=10)

# Scopes
SCOPE_BALANCES = "balances"
SCOPE_DETAILS = "details"
SCOPE_TRANSACTIONS = "transactions"

# Storage schema
STORAGE_VERSION = 1

# Institution filtering
IGNORED_INSTITUTION_PREFIXES = ("SANDBOXFINANCE_",)
