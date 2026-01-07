"""Data update coordinator for GoCardless Bank Account Data."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import GoCardlessAPIClient
from .const import (
    DOMAIN,
    RATE_LIMIT_BALANCES,
    RATE_LIMIT_DETAILS,
    RATE_LIMIT_TRANSACTIONS,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_INTERVAL_REQUISITIONS,
)

_LOGGER = logging.getLogger(__name__)


class GoCardlessDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching GoCardless data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: GoCardlessAPIClient,
        entry_id: str,
    ) -> None:
        """Initialize the data update coordinator."""
        self.api_client = api_client
        self._entry_id = entry_id
        
        # Storage for account data persistence
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_data_{entry_id}",
        )
        
        # Cache institution names to avoid repeated API calls
        self._institution_names: dict[str, str] = {}
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL_REQUISITIONS,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Try to load cached account data first (to preserve on restart)
            cached_data = await self._store.async_load()
            cached_accounts = {}
            if cached_data:
                cached_accounts = cached_data.get("accounts", {})
                _LOGGER.info("Loaded cached data for %d accounts from storage", len(cached_accounts))
            
            # Fetch all requisitions (this is safe - 300/min limit)
            requisitions = await self.api_client.get_requisitions()
            
            # Structure to hold all account data
            accounts_data: dict[str, Any] = {}
            
            for requisition in requisitions:
                requisition_id = requisition.get("id")
                status = requisition.get("status")
                
                # Only process linked requisitions
                if status != "LN":  # LN = Linked
                    continue
                
                # Get accounts from this requisition
                account_ids = requisition.get("accounts", [])
                
                for account_id in account_ids:
                    if account_id not in accounts_data:
                        # Start with cached data if available
                        if account_id in cached_accounts:
                            accounts_data[account_id] = cached_accounts[account_id]
                            # Update requisition info in case it changed
                            accounts_data[account_id]["requisition_id"] = requisition_id
                            accounts_data[account_id]["institution_id"] = requisition.get("institution_id")
                            _LOGGER.debug("Restored cached data for account %s", account_id)
                        else:
                            # No cached data, initialize empty
                            accounts_data[account_id] = {
                                "id": account_id,
                                "requisition_id": requisition_id,
                                "institution_id": requisition.get("institution_id"),
                                "details": None,
                                "balances": None,
                                "transactions": None,
                            }
            
            # Fetch institution names for linked accounts (cache for sensor naming)
            unique_institutions = set(
                acc.get("institution_id") for acc in accounts_data.values() 
                if acc.get("institution_id")
            )
            
            for inst_id in unique_institutions:
                if inst_id and inst_id not in self._institution_names:
                    inst_info = await self.api_client.get_institution(inst_id)
                    if inst_info:
                        self._institution_names[inst_id] = inst_info.get("name", inst_id)
                        _LOGGER.debug("Cached institution name: %s = %s", inst_id, inst_info.get("name"))
            
            # Store the result temporarily so _populate_missing_data can access it
            temp_result = {
                "requisitions": requisitions,
                "accounts": accounts_data,
                "institution_names": self._institution_names,
            }
            
            # Update self.data temporarily so populate method can work
            if not self.data:
                self.data = temp_result
            else:
                self.data.update(temp_result)
            
            # Check for accounts with missing data and fetch it
            await self._populate_missing_data(accounts_data)
            
            # Return updated data
            return self.data
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _populate_missing_data(self, accounts_data: dict[str, Any]) -> None:
        """Populate missing balance/details data for accounts."""
        for account_id, account_info in accounts_data.items():
            # Check if details are missing
            if not account_info.get("details"):
                _LOGGER.info("Fetching missing details for account %s", account_id)
                try:
                    await self.async_update_account_details(account_id)
                except Exception as err:
                    _LOGGER.error("Failed to fetch initial details for %s: %s", account_id, err)
            
            # Check if balances are missing
            if not account_info.get("balances"):
                _LOGGER.info("Fetching missing balances for account %s", account_id)
                try:
                    await self.async_update_account_balances(account_id)
                except Exception as err:
                    _LOGGER.error("Failed to fetch initial balances for %s: %s", account_id, err)

    async def async_update_account_details(self, account_id: str) -> dict[str, Any] | None:
        """Update account details for a specific account."""
        try:
            details = await self.api_client.get_account_details(
                account_id, max_per_day=RATE_LIMIT_DETAILS
            )
            
            if details and self.data:
                if account_id in self.data["accounts"]:
                    self.data["accounts"][account_id]["details"] = details
                    self.data["accounts"][account_id]["details_updated"] = datetime.now().isoformat()
                    self.async_set_updated_data(self.data)
                    # Save to storage
                    await self._save_account_data()
            
            return details
        except Exception as err:
            _LOGGER.error("Failed to update account details for %s: %s", account_id, err)
            return None

    async def async_update_account_balances(self, account_id: str) -> dict[str, Any] | None:
        """Update account balances for a specific account."""
        try:
            balances = await self.api_client.get_account_balances(
                account_id, max_per_day=RATE_LIMIT_BALANCES
            )
            
            if balances and self.data:
                if account_id in self.data["accounts"]:
                    self.data["accounts"][account_id]["balances"] = balances
                    self.data["accounts"][account_id]["balances_updated"] = datetime.now().isoformat()
                    self.async_set_updated_data(self.data)
                    # Save to storage
                    await self._save_account_data()
            
            return balances
        except Exception as err:
            _LOGGER.error("Failed to update account balances for %s: %s", account_id, err)
            return None

    async def async_update_account_transactions(self, account_id: str) -> dict[str, Any] | None:
        """Update account transactions for a specific account."""
        try:
            transactions = await self.api_client.get_account_transactions(
                account_id, max_per_day=RATE_LIMIT_TRANSACTIONS
            )
            
            if transactions and self.data:
                if account_id in self.data["accounts"]:
                    self.data["accounts"][account_id]["transactions"] = transactions
                    self.data["accounts"][account_id]["transactions_updated"] = datetime.now().isoformat()
                    self.async_set_updated_data(self.data)
                    # Save to storage
                    await self._save_account_data()
            
            return transactions
        except Exception as err:
            _LOGGER.error(
                "Failed to update account transactions for %s: %s", account_id, err
            )
            return None

    async def _save_account_data(self) -> None:
        """Save account data to storage."""
        if not self.data:
            return
        
        save_data = {
            "accounts": self.data.get("accounts", {}),
            "saved_at": datetime.now().isoformat(),
        }
        
        await self._store.async_save(save_data)
        _LOGGER.debug("Saved account data to storage")

