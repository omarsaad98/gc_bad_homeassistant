"""Unit tests for snapshot contract behavior."""
from __future__ import annotations

from custom_components.gc_bad.models import AccountSnapshot, IntegrationSnapshot


def test_account_snapshot_roundtrip() -> None:
    """Typed account snapshot should serialize and deserialize cleanly."""
    account = AccountSnapshot.from_api(
        account_id="acc_1",
        requisition_id="req_1",
        institution_id="bank_1",
        details_payload={"account": {"name": "Main", "iban": "IBAN1"}},
        balances_payload={
            "balances": [
                {
                    "balanceAmount": {"amount": "10.5", "currency": "EUR"},
                    "balanceType": "interimAvailable",
                    "referenceDate": "2026-01-01",
                }
            ]
        },
        details_updated="2026-01-01T00:00:00+00:00",
        balances_updated="2026-01-01T00:00:00+00:00",
    )
    restored = AccountSnapshot.from_dict(account.as_dict())
    assert restored.id == "acc_1"
    assert restored.account_name == "Main"
    assert restored.balances[0].currency == "EUR"


def test_integration_snapshot_roundtrip() -> None:
    """Integration snapshot should preserve account mapping."""
    account = AccountSnapshot.from_api(
        account_id="acc_1",
        requisition_id="req_1",
        institution_id="bank_1",
        details_payload={"account": {"name": "Main", "iban": "IBAN1"}},
        balances_payload={"balances": []},
        details_updated=None,
        balances_updated=None,
    )
    snapshot = IntegrationSnapshot(
        accounts={"acc_1": account},
        institution_names={"bank_1": "My Bank"},
        last_successful_refresh="2026-01-01T00:00:00+00:00",
    )
    restored = IntegrationSnapshot.from_dict(snapshot.as_dict())
    assert "acc_1" in restored.accounts
    assert restored.institution_names["bank_1"] == "My Bank"
