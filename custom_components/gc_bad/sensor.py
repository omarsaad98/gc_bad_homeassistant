"""Sensor platform for GoCardless Bank Account Data integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, UPDATE_INTERVAL_BALANCES
from .coordinator import GoCardlessDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GoCardless sensors based on a config entry."""
    coordinator: GoCardlessDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]["coordinator"]

    entities: list[SensorEntity] = []

    # Create sensors for each account
    if coordinator.data and "accounts" in coordinator.data:
        for account_id, account_data in coordinator.data["accounts"].items():
            # Add balance sensor
            entities.append(
                GoCardlessAccountBalanceSensor(coordinator, account_id, account_data)
            )
            
            # Add account details sensor
            entities.append(
                GoCardlessAccountDetailsSensor(coordinator, account_id, account_data)
            )

    async_add_entities(entities)


class GoCardlessAccountBalanceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for account balance."""

    def __init__(
        self,
        coordinator: GoCardlessDataUpdateCoordinator,
        account_id: str,
        account_data: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_id = account_id
        
        # Get resourceId from details if available
        resource_id = None
        if account_data.get("details"):
            account_info = account_data["details"].get("account", {})
            resource_id = account_info.get("resourceId")
        
        # Use resourceId for unique_id if available, otherwise use account_id
        self._attr_unique_id = f"{resource_id or account_id}_balance"
        
        # Don't set _attr_name here - use dynamic name property instead
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._last_balance_update: datetime | None = None

    @property
    def name(self) -> str:
        """Return the name of the sensor (dynamic based on current data)."""
        if not self.coordinator.data:
            return f"Account {self._account_id[-4:]} Balance"
        
        account_data = self.coordinator.data.get("accounts", {}).get(self._account_id)
        if not account_data:
            return f"Account {self._account_id[-4:]} Balance"
        
        # Get account name from details
        account_name = None
        if account_data.get("details"):
            account_info = account_data["details"].get("account", {})
            account_name = account_info.get("name")
        
        # Get institution name from coordinator cache
        institution_id = account_data.get("institution_id", "")
        institution_name = None
        if institution_id:
            institution_names = self.coordinator.data.get("institution_names", {})
            institution_name = institution_names.get(institution_id)
            
            # Fallback: Extract from institution_id
            if not institution_name:
                institution_name = institution_id.split("_")[0].title()
        
        # Build name with institution and account name
        if institution_name and account_name:
            return f"{institution_name} {account_name} Balance"
        elif account_name:
            return f"{account_name} Balance"
        elif institution_name:
            return f"{institution_name} Account {self._account_id[-4:]} Balance"
        else:
            return f"Account {self._account_id[-4:]} Balance"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        account_data = self.coordinator.data["accounts"].get(self._account_id)
        if not account_data:
            return None
        
        balances = account_data.get("balances")
        if not balances or "balances" not in balances:
            return None
        
        # Get the first available balance
        balance_list = balances["balances"]
        if balance_list and len(balance_list) > 0:
            balance_info = balance_list[0]
            amount = balance_info.get("balanceAmount", {}).get("amount")
            if amount:
                try:
                    return float(amount)
                except (ValueError, TypeError):
                    return None
        
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if not self.coordinator.data:
            return None
        
        account_data = self.coordinator.data["accounts"].get(self._account_id)
        if not account_data:
            return None
        
        balances = account_data.get("balances")
        if not balances or "balances" not in balances:
            return None
        
        # Get currency from the first available balance
        balance_list = balances["balances"]
        if balance_list and len(balance_list) > 0:
            balance_info = balance_list[0]
            return balance_info.get("balanceAmount", {}).get("currency")
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return None
        
        account_data = self.coordinator.data["accounts"].get(self._account_id)
        if not account_data:
            return None
        
        attributes = {
            "account_id": self._account_id,
            "requisition_id": account_data.get("requisition_id"),
            "institution_id": account_data.get("institution_id"),
        }
        
        balances = account_data.get("balances")
        if balances and "balances" in balances:
            balance_list = balances["balances"]
            if balance_list and len(balance_list) > 0:
                balance_info = balance_list[0]
                attributes["balance_type"] = balance_info.get("balanceType")
                attributes["reference_date"] = balance_info.get("referenceDate")
        
        return attributes

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, ensure we have balance data."""
        await super().async_added_to_hass()
        # The coordinator now populates missing data automatically
        # Just mark when we're ready
        if self.coordinator.data:
            account_data = self.coordinator.data.get("accounts", {}).get(self._account_id)
            if account_data and account_data.get("balances"):
                self._last_balance_update = datetime.now()
                _LOGGER.debug("Balance sensor ready for %s", self._account_id)

    async def async_update(self) -> None:
        """Update the sensor - respecting rate limits."""
        # Only update if enough time has passed
        now = datetime.now()
        if self._last_balance_update:
            time_since_update = now - self._last_balance_update
            if time_since_update < UPDATE_INTERVAL_BALANCES:
                _LOGGER.debug(
                    "Skipping balance update for %s - too soon (last: %s ago)",
                    self._account_id,
                    time_since_update,
                )
                return
        
        # Request balance update
        await self.coordinator.async_update_account_balances(self._account_id)
        self._last_balance_update = now

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class GoCardlessAccountDetailsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for account details (IBAN, name, etc.)."""

    def __init__(
        self,
        coordinator: GoCardlessDataUpdateCoordinator,
        account_id: str,
        account_data: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_id = account_id
        
        # Use resourceId for unique_id if available from account_data
        resource_id = None
        if account_data.get("details"):
            account_info = account_data["details"].get("account", {})
            resource_id = account_info.get("resourceId")
        
        # Use resourceId for unique_id if available, otherwise use account_id
        self._attr_unique_id = f"{resource_id or account_id}_details"
        
        # Name will be set dynamically in the name property
        self._last_details_update: datetime | None = None

    @property
    def name(self) -> str:
        """Return the name of the sensor (dynamic based on current data)."""
        if not self.coordinator.data:
            return f"Account {self._account_id[-4:]} Details"
        
        account_data = self.coordinator.data.get("accounts", {}).get(self._account_id)
        if not account_data:
            return f"Account {self._account_id[-4:]} Details"
        
        # Get account name from details
        account_name = None
        if account_data.get("details"):
            account_info = account_data["details"].get("account", {})
            account_name = account_info.get("name")
        
        # Get institution name from coordinator cache
        institution_id = account_data.get("institution_id", "")
        institution_name = None
        if institution_id:
            institution_names = self.coordinator.data.get("institution_names", {})
            institution_name = institution_names.get(institution_id)
            
            # Fallback: Extract from institution_id
            if not institution_name:
                institution_name = institution_id.split("_")[0].title()
        
        # Build name with institution and account name
        if institution_name and account_name:
            return f"{institution_name} {account_name} Details"
        elif account_name:
            return f"{account_name} Details"
        elif institution_name:
            return f"{institution_name} Account {self._account_id[-4:]} Details"
        else:
            return f"Account {self._account_id[-4:]} Details"

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, ensure we have details data."""
        await super().async_added_to_hass()
        # The coordinator now populates missing data automatically
        # Just mark when we're ready
        if self.coordinator.data:
            account_data = self.coordinator.data.get("accounts", {}).get(self._account_id)
            if account_data and account_data.get("details"):
                self._last_details_update = datetime.now()
                _LOGGER.debug("Details sensor ready for %s", self._account_id)

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor (IBAN or account name)."""
        if not self.coordinator.data:
            return None
        
        account_data = self.coordinator.data["accounts"].get(self._account_id)
        if not account_data:
            return None
        
        details = account_data.get("details")
        if not details or "account" not in details:
            return "Not loaded"
        
        account_info = details["account"]
        # Return IBAN if available, otherwise account name
        return account_info.get("iban") or account_info.get("name") or "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return None
        
        account_data = self.coordinator.data["accounts"].get(self._account_id)
        if not account_data:
            return None
        
        attributes = {
            "account_id": self._account_id,
            "requisition_id": account_data.get("requisition_id"),
            "institution_id": account_data.get("institution_id"),
        }
        
        details = account_data.get("details")
        if details and "account" in details:
            account_info = details["account"]
            attributes["iban"] = account_info.get("iban")
            attributes["name"] = account_info.get("name")
            attributes["currency"] = account_info.get("currency")
            attributes["owner_name"] = account_info.get("ownerName")
            attributes["status"] = account_info.get("status")
        
        return attributes

    async def async_update(self) -> None:
        """Update the sensor - respecting rate limits."""
        # Only update if enough time has passed
        now = datetime.now()
        if self._last_details_update:
            time_since_update = now - self._last_details_update
            # Use same interval as balances
            if time_since_update < UPDATE_INTERVAL_BALANCES:
                _LOGGER.debug(
                    "Skipping details update for %s - too soon (last: %s ago)",
                    self._account_id,
                    time_since_update,
                )
                return
        
        # Request details update
        await self.coordinator.async_update_account_details(self._account_id)
        self._last_details_update = now

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

