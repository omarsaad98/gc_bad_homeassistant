"""Data update coordinator for GoCardless Bank Account Data."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import GoCardlessAPIClient
from .const import (
    DOMAIN,
    RATE_LIMIT_BALANCES,
    RATE_LIMIT_DETAILS,
    RATE_LIMIT_TRANSACTIONS,
    UPDATE_INTERVAL_REQUISITIONS,
)

_LOGGER = logging.getLogger(__name__)


class GoCardlessDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching GoCardless data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: GoCardlessAPIClient,
    ) -> None:
        """Initialize the data update coordinator."""
        self.api_client = api_client
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL_REQUISITIONS,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Fetch all requisitions
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
                        accounts_data[account_id] = {
                            "id": account_id,
                            "requisition_id": requisition_id,
                            "institution_id": requisition.get("institution_id"),
                            "details": None,
                            "balances": None,
                            "transactions": None,
                        }
            
            return {
                "requisitions": requisitions,
                "accounts": accounts_data,
            }
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_update_account_details(self, account_id: str) -> dict[str, Any] | None:
        """Update account details for a specific account."""
        try:
            details = await self.api_client.get_account_details(
                account_id, max_per_day=RATE_LIMIT_DETAILS
            )
            
            if details and self.data:
                if account_id in self.data["accounts"]:
                    self.data["accounts"][account_id]["details"] = details
                    self.async_set_updated_data(self.data)
            
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
                    self.async_set_updated_data(self.data)
            
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
                    self.async_set_updated_data(self.data)
            
            return transactions
        except Exception as err:
            _LOGGER.error(
                "Failed to update account transactions for %s: %s", account_id, err
            )
            return None

