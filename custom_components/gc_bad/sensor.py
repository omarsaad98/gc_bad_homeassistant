"""Sensor platform for GoCardless Bank Account Data integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import GCBadRuntimeData
from .entity import GCBadBaseEntity
from .models import BalanceSnapshot


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up balance sensors from coordinator snapshot."""
    runtime_data: GCBadRuntimeData = config_entry.runtime_data
    snapshot = runtime_data.coordinator.data
    if snapshot is None:
        return

    entities: list[SensorEntity] = []
    for account in snapshot.accounts.values():
        for balance in account.balances:
            entities.append(
                GoCardlessAccountBalanceSensor(
                    runtime_data.coordinator,
                    account.id,
                    currency=balance.currency,
                    balance_type=balance.balance_type,
                )
            )

    async_add_entities(entities)


class GoCardlessAccountBalanceSensor(GCBadBaseEntity, RestoreSensor):
    """Sensor for one account balance selection."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator,
        account_id: str,
        *,
        currency: str | None,
        balance_type: str | None,
    ) -> None:
        """Initialize balance sensor."""
        super().__init__(coordinator, account_id)
        self._currency = currency
        self._balance_type = balance_type
        currency_part = currency or "unknown_currency"
        type_part = balance_type or "unknown_type"
        self._attr_unique_id = f"{account_id}_{currency_part}_{type_part}"
        self._restored_attributes: dict[str, Any] | None = None

    def _selected_balance(self) -> BalanceSnapshot | None:
        """Return the balance this sensor projects."""
        account = self.account
        if account is None:
            return None
        return account.find_balance(currency=self._currency, balance_type=self._balance_type)

    @property
    def name(self) -> str:
        """Return display name."""
        account = self.account
        if account is None:
            return f"Account {self._account_id[-4:]} balance"

        snapshot = self.coordinator.data
        institution_name = None
        if snapshot and account.institution_id:
            institution_name = snapshot.institution_names.get(account.institution_id)

        base = account.account_name or f"Account {self._account_id[-4:]}"
        if institution_name:
            base = f"{institution_name} {base}"

        if self._balance_type:
            return f"{base} {self._balance_type}"
        return base

    @property
    def native_value(self) -> float | None:
        """Return current balance amount."""
        selected = self._selected_balance()
        if selected is not None:
            return selected.amount
        return self._attr_native_value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return balance currency."""
        selected = self._selected_balance()
        if selected is not None:
            return selected.currency
        return self._attr_native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return detailed metadata for this balance."""
        account = self.account
        if account is None:
            return self._restored_attributes

        selected = self._selected_balance()
        last_success = self.coordinator.last_successful_refresh
        return {
            "account_id": account.id,
            "requisition_id": account.requisition_id,
            "institution_id": account.institution_id,
            "iban": account.iban,
            "balance_type": selected.balance_type if selected else self._balance_type,
            "currency": selected.currency if selected else self._currency,
            "reference_date": selected.reference_date if selected else None,
            "data_stale": not self.coordinator.last_update_success,
            "last_successful_refresh": (
                dt_util.as_local(last_success).isoformat() if last_success else None
            ),
        }

    async def async_added_to_hass(self) -> None:
        """Restore last known state if coordinator data is absent."""
        await super().async_added_to_hass()
        restored = await self.async_get_last_sensor_data()
        if restored is None:
            return
        self._attr_native_value = restored.native_value
        self._attr_native_unit_of_measurement = restored.native_unit_of_measurement
        if restored.extra_attributes:
            self._restored_attributes = dict(restored.extra_attributes)

