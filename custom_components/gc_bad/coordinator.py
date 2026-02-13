"""Data update coordinator for GoCardless Bank Account Data."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.config_entries import ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api.client import (
    GCBadApiError,
    GCBadCannotConnectError,
    GCBadRateLimitError,
    GoCardlessApiClient,
)
from .const import (
    DOMAIN,
    IGNORED_INSTITUTION_PREFIXES,
    RATE_LIMIT_BALANCES,
    RATE_LIMIT_DETAILS,
    UPDATE_INTERVAL_BALANCES,
)
from .models import AccountSnapshot, IntegrationSnapshot
from .storage import IntegrationStorage

_LOGGER = logging.getLogger(__name__)


class GoCardlessDataUpdateCoordinator(DataUpdateCoordinator[IntegrationSnapshot]):
    """Coordinator that owns the integration snapshot lifecycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: GoCardlessApiClient,
        storage: IntegrationStorage,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self._api_client = api_client
        self._storage = storage

    async def _async_setup(self) -> None:
        """Load cached snapshot once before first refresh."""
        cached = await self._storage.load_snapshot()
        if cached:
            self.data = cached

    @property
    def last_successful_refresh(self) -> datetime | None:
        """Expose last successful refresh for scheduling logic."""
        if not self.data:
            return None
        return self.data.get_last_successful_refresh_dt()

    async def _async_update_data(self) -> IntegrationSnapshot:
        """Fetch requisitions and refresh account snapshot."""
        previous = self.data or IntegrationSnapshot()
        accounts = dict(previous.accounts)
        institution_names = dict(previous.institution_names)

        try:
            requisitions = await self._api_client.get_requisitions()
            for requisition in requisitions:
                if requisition.get("status") != "LN":
                    continue
                institution_id = requisition.get("institution_id", "")
                if institution_id.startswith(IGNORED_INSTITUTION_PREFIXES):
                    continue
                requisition_id = requisition.get("id")
                account_ids = requisition.get("accounts", [])
                for account_id in account_ids:
                    if not isinstance(account_id, str):
                        continue
                    previous_account = accounts.get(account_id)
                    details_payload = previous_account.details if previous_account else None
                    balances_payload = self._to_balances_payload(previous_account)
                    details_updated = previous_account.details_updated if previous_account else None
                    balances_updated = previous_account.balances_updated if previous_account else None

                    if details_payload is None:
                        details_payload = await self._api_client.get_account_details(
                            account_id,
                            max_per_day=RATE_LIMIT_DETAILS,
                        )
                        details_updated = dt_util.utcnow().isoformat()

                    should_refresh_balance = self._should_refresh_balances(previous_account)
                    if balances_payload is None or should_refresh_balance:
                        balances_payload = await self._api_client.get_account_balances(
                            account_id,
                            max_per_day=RATE_LIMIT_BALANCES,
                        )
                        balances_updated = dt_util.utcnow().isoformat()

                    accounts[account_id] = AccountSnapshot.from_api(
                        account_id=account_id,
                        requisition_id=requisition_id,
                        institution_id=institution_id,
                        details_payload=details_payload,
                        balances_payload=balances_payload,
                        details_updated=details_updated,
                        balances_updated=balances_updated,
                    )

                    if institution_id and institution_id not in institution_names:
                        institution = await self._api_client.get_institution(institution_id)
                        institution_names[institution_id] = institution.get("name", institution_id)

        except GCBadCannotConnectError as err:
            raise UpdateFailed(str(err)) from err
        except GCBadRateLimitError as err:
            raise UpdateFailed(str(err)) from err
        except GCBadApiError as err:
            if "Authentication failed" in str(err):
                raise ConfigEntryAuthFailed(str(err)) from err
            raise UpdateFailed(str(err)) from err

        refreshed_at = dt_util.utcnow()
        snapshot = IntegrationSnapshot(
            accounts=accounts,
            institution_names=institution_names,
            last_successful_refresh=refreshed_at.isoformat(),
        )
        await self._storage.save_snapshot(snapshot, refreshed_at)
        return snapshot

    def _should_refresh_balances(self, account: AccountSnapshot | None) -> bool:
        """Return True when balance data is absent or stale."""
        if account is None or not account.balances:
            return True
        if not account.balances_updated:
            return True
        parsed = dt_util.parse_datetime(account.balances_updated)
        if parsed is None:
            return True
        return (dt_util.utcnow() - parsed) >= UPDATE_INTERVAL_BALANCES

    def _to_balances_payload(self, account: AccountSnapshot | None) -> dict | None:
        """Convert typed balances back to minimal API-like payload."""
        if account is None or not account.balances:
            return None
        return {
            "balances": [
                {
                    "balanceAmount": {
                        "amount": balance.amount,
                        "currency": balance.currency,
                    },
                    "balanceType": balance.balance_type,
                    "referenceDate": balance.reference_date,
                }
                for balance in account.balances
            ]
        }

