"""Unit tests for balance sensor projection logic."""
from __future__ import annotations

from custom_components.gc_bad.models import AccountSnapshot, BalanceSnapshot, IntegrationSnapshot
from custom_components.gc_bad.sensor import GoCardlessAccountBalanceSensor


class DummyCoordinator:
    """Small coordinator stub for sensor tests."""

    def __init__(self, snapshot: IntegrationSnapshot) -> None:
        self.data = snapshot
        self.last_update_success = True

    @property
    def last_successful_refresh(self):
        return self.data.get_last_successful_refresh_dt()


def test_balance_sensor_reads_selected_balance() -> None:
    """Sensor should project amount/unit from one selected balance."""
    account = AccountSnapshot(
        id="acc_1",
        requisition_id="req_1",
        institution_id="bank_1",
        account_name="Main Account",
        iban="IBAN",
        details={"account": {"name": "Main Account"}},
        balances=[
            BalanceSnapshot(
                amount=25.4,
                currency="EUR",
                balance_type="interimAvailable",
                reference_date="2026-01-01",
            )
        ],
        details_updated="2026-01-01T00:00:00+00:00",
        balances_updated="2026-01-01T00:00:00+00:00",
    )
    snapshot = IntegrationSnapshot(
        accounts={"acc_1": account},
        institution_names={"bank_1": "Bank"},
        last_successful_refresh="2026-01-01T00:00:00+00:00",
    )
    coordinator = DummyCoordinator(snapshot)
    sensor = GoCardlessAccountBalanceSensor(
        coordinator,
        "acc_1",
        currency="EUR",
        balance_type="interimAvailable",
    )

    assert sensor.native_value == 25.4
    assert sensor.native_unit_of_measurement == "EUR"
    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert attrs["institution_id"] == "bank_1"
    assert attrs["balance_type"] == "interimAvailable"
