"""Sensor platform for GoCardless Bank Account Data integration."""
from __future__ import annotations

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
        self._attr_unique_id = f"{account_id}_balance"
        self._attr_name = f"Account {account_id[-4:]} Balance"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._last_balance_update: datetime | None = None

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
        """When entity is added to hass, fetch initial balance data."""
        await super().async_added_to_hass()
        # Fetch initial balance data
        await self.coordinator.async_update_account_balances(self._account_id)
        self._last_balance_update = datetime.now()

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
        self._attr_unique_id = f"{account_id}_details"
        self._attr_name = f"Account {account_id[-4:]} Details"
        self._last_details_update: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, fetch initial details data."""
        await super().async_added_to_hass()
        # Fetch initial details data
        await self.coordinator.async_update_account_details(self._account_id)
        self._last_details_update = datetime.now()

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

