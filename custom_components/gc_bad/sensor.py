"""Sensor platform for GoCardless Bank Account Data integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

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

    # Create sensors for each balance in each account
    if coordinator.data and "accounts" in coordinator.data:
        for account_id, account_data in coordinator.data["accounts"].items():
            balances_data = account_data.get("balances") or {}
            balances = balances_data.get("balances", [])
            if not isinstance(balances, list):
                balances = []
            for balance in balances:
                currency = balance.get("balanceAmount", {}).get("currency")
                balance_type = balance.get("balanceType")
                entities.append(
                    GoCardlessAccountBalanceSensor(
                        coordinator,
                        account_id,
                        account_data,
                        balance_type=balance_type,
                        currency=currency,
                    )
                )

    async_add_entities(entities)


class GoCardlessAccountBalanceSensor(CoordinatorEntity, RestoreSensor):
    """Sensor for account balance."""

    def __init__(
        self,
        coordinator: GoCardlessDataUpdateCoordinator,
        account_id: str,
        account_data: dict[str, Any],
        *,
        balance_type: str | None,
        currency: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_id = account_id
        self._balance_type = balance_type
        self._balance_currency = currency or "UNKNOWN"
        
        # Get resourceId from details if available
        resource_id = None
        if account_data.get("details"):
            account_info = account_data["details"].get("account", {})
            resource_id = account_info.get("resourceId")
        
        # Use account id + currency for unique_id (per-balance sensor)
        self._attr_unique_id = f"{account_id}_{self._balance_currency}"
        
        # Don't set _attr_name here - use dynamic name property instead
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._last_balance_update: datetime | None = None
        self._restored_attributes: dict[str, Any] | None = None

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
            return f"{institution_name} {account_name}"
        elif account_name:
            return f"{account_name}"
        elif institution_name:
            return f"{institution_name} Account {self._account_id[-4:]}"
        else:
            return f"Account {self._account_id[-4:]}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return self._attr_native_value
        
        account_data = self.coordinator.data["accounts"].get(self._account_id)
        if not account_data:
            return self._attr_native_value
        
        balances = account_data.get("balances")
        if not balances or "balances" not in balances:
            return self._attr_native_value
        
        # Get the balance that matches this sensor's currency (and type if present)
        balance_list = balances["balances"]
        for balance_info in balance_list:
            if (
                balance_info.get("balanceAmount", {}).get("currency")
                != self._balance_currency
            ):
                continue
            if self._balance_type and balance_info.get("balanceType") != self._balance_type:
                continue
            amount = balance_info.get("balanceAmount", {}).get("amount")
            if amount:
                try:
                    return float(amount)
                except (ValueError, TypeError):
                    return self._attr_native_value
        
        return self._attr_native_value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if not self.coordinator.data:
            return self._attr_native_unit_of_measurement
        
        account_data = self.coordinator.data["accounts"].get(self._account_id)
        if not account_data:
            return self._attr_native_unit_of_measurement
        
        balances = account_data.get("balances")
        if not balances or "balances" not in balances:
            return self._attr_native_unit_of_measurement
        
        # Get currency from the matching balance
        balance_list = balances["balances"]
        for balance_info in balance_list:
            currency = balance_info.get("balanceAmount", {}).get("currency")
            if currency != self._balance_currency:
                continue
            if self._balance_type and balance_info.get("balanceType") != self._balance_type:
                continue
            return currency
        
        return self._attr_native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return self._restored_attributes
        
        account_data = self.coordinator.data["accounts"].get(self._account_id)
        if not account_data:
            return self._restored_attributes
        
        attributes = {
            "account_id": self._account_id,
            "requisition_id": account_data.get("requisition_id"),
            "institution_id": account_data.get("institution_id"),
            "currency": self._balance_currency,
        }
        
        balances = account_data.get("balances")
        if balances and "balances" in balances:
            balance_list = balances["balances"]
            for balance_info in balance_list:
                if (
                    balance_info.get("balanceAmount", {}).get("currency")
                    != self._balance_currency
                ):
                    continue
                if self._balance_type and balance_info.get("balanceType") != self._balance_type:
                    continue
                attributes["balance_type"] = balance_info.get("balanceType")
                attributes["reference_date"] = balance_info.get("referenceDate")
                break

        attributes["data_stale"] = not self.coordinator.last_update_success
        last_success = self.coordinator.last_successful_refresh
        attributes["last_successful_refresh"] = (
            dt_util.as_local(last_success).isoformat() if last_success else None
        )
        
        return attributes

    @property
    def available(self) -> bool:
        """Return True if cached data exists, even when updates fail."""
        if super().available:
            return True
        return self._has_cached_balance()

    def _has_cached_balance(self) -> bool:
        """Check if cached data can provide a balance value."""
        if self._attr_native_value is not None:
            return True

        if not self.coordinator.data:
            return False

        account_data = self.coordinator.data.get("accounts", {}).get(self._account_id)
        if not account_data:
            return False

        balances = account_data.get("balances")
        if not balances or "balances" not in balances:
            return False

        for balance_info in balances["balances"]:
            if (
                balance_info.get("balanceAmount", {}).get("currency")
                != self._balance_currency
            ):
                continue
            if self._balance_type and balance_info.get("balanceType") != self._balance_type:
                continue
            amount = balance_info.get("balanceAmount", {}).get("amount")
            if amount is not None:
                return True

        return False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, ensure we have balance data."""
        await super().async_added_to_hass()
        if restored := await self.async_get_last_sensor_data():
            self._attr_native_value = restored.native_value
            self._attr_native_unit_of_measurement = (
                restored.native_unit_of_measurement
            )
            if restored.extra_attributes:
                self._restored_attributes = dict(restored.extra_attributes)

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

