"""Typed models for integration runtime snapshots."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util


@dataclass(slots=True)
class BalanceSnapshot:
    """Normalized view of a single balance entry."""

    amount: float | None
    currency: str | None
    balance_type: str | None
    reference_date: str | None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "BalanceSnapshot":
        """Create a typed balance snapshot from API payload."""
        amount_raw = raw.get("balanceAmount", {}).get("amount")
        amount: float | None = None
        if amount_raw is not None:
            try:
                amount = float(amount_raw)
            except (TypeError, ValueError):
                amount = None

        return cls(
            amount=amount,
            currency=raw.get("balanceAmount", {}).get("currency"),
            balance_type=raw.get("balanceType"),
            reference_date=raw.get("referenceDate"),
        )

    def as_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "amount": self.amount,
            "currency": self.currency,
            "balance_type": self.balance_type,
            "reference_date": self.reference_date,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BalanceSnapshot":
        """Deserialize from storage."""
        return cls(
            amount=data.get("amount"),
            currency=data.get("currency"),
            balance_type=data.get("balance_type"),
            reference_date=data.get("reference_date"),
        )


@dataclass(slots=True)
class AccountSnapshot:
    """Normalized account state used by entities."""

    id: str
    requisition_id: str | None
    institution_id: str | None
    account_name: str | None
    iban: str | None
    details: dict[str, Any] | None
    balances: list[BalanceSnapshot] = field(default_factory=list)
    details_updated: str | None = None
    balances_updated: str | None = None

    @classmethod
    def from_api(
        cls,
        account_id: str,
        requisition_id: str | None,
        institution_id: str | None,
        details_payload: dict[str, Any] | None,
        balances_payload: dict[str, Any] | None,
        details_updated: str | None,
        balances_updated: str | None,
    ) -> "AccountSnapshot":
        """Build a typed account snapshot from API payloads."""
        account_obj = (details_payload or {}).get("account", {})
        raw_balances = (balances_payload or {}).get("balances", [])
        balances = [
            BalanceSnapshot.from_raw(raw_item)
            for raw_item in raw_balances
            if isinstance(raw_item, dict)
        ]

        return cls(
            id=account_id,
            requisition_id=requisition_id,
            institution_id=institution_id,
            account_name=account_obj.get("name"),
            iban=account_obj.get("iban"),
            details=details_payload,
            balances=balances,
            details_updated=details_updated,
            balances_updated=balances_updated,
        )

    def find_balance(
        self,
        *,
        currency: str | None,
        balance_type: str | None,
    ) -> BalanceSnapshot | None:
        """Find the first matching balance for a sensor."""
        for item in self.balances:
            if currency and item.currency != currency:
                continue
            if balance_type and item.balance_type != balance_type:
                continue
            return item
        return None

    def as_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "id": self.id,
            "requisition_id": self.requisition_id,
            "institution_id": self.institution_id,
            "account_name": self.account_name,
            "iban": self.iban,
            "details": self.details,
            "balances": [balance.as_dict() for balance in self.balances],
            "details_updated": self.details_updated,
            "balances_updated": self.balances_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AccountSnapshot":
        """Deserialize from storage."""
        return cls(
            id=data["id"],
            requisition_id=data.get("requisition_id"),
            institution_id=data.get("institution_id"),
            account_name=data.get("account_name"),
            iban=data.get("iban"),
            details=data.get("details"),
            balances=[
                BalanceSnapshot.from_dict(item)
                for item in data.get("balances", [])
                if isinstance(item, dict)
            ],
            details_updated=data.get("details_updated"),
            balances_updated=data.get("balances_updated"),
        )


@dataclass(slots=True)
class IntegrationSnapshot:
    """Coordinator state consumed by platforms."""

    accounts: dict[str, AccountSnapshot] = field(default_factory=dict)
    institution_names: dict[str, str] = field(default_factory=dict)
    last_successful_refresh: str | None = None

    def get_last_successful_refresh_dt(self) -> datetime | None:
        """Parse the last refresh into datetime."""
        if not self.last_successful_refresh:
            return None
        return dt_util.parse_datetime(self.last_successful_refresh)

    def as_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "accounts": {
                account_id: account.as_dict()
                for account_id, account in self.accounts.items()
            },
            "institution_names": self.institution_names,
            "last_successful_refresh": self.last_successful_refresh,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntegrationSnapshot":
        """Deserialize from storage."""
        accounts: dict[str, AccountSnapshot] = {}
        for account_id, account_data in data.get("accounts", {}).items():
            if isinstance(account_data, dict):
                accounts[account_id] = AccountSnapshot.from_dict(account_data)

        return cls(
            accounts=accounts,
            institution_names=dict(data.get("institution_names", {})),
            last_successful_refresh=data.get("last_successful_refresh"),
        )
