"""Base entities for the integration."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GoCardlessDataUpdateCoordinator
from .models import AccountSnapshot


class GCBadBaseEntity(CoordinatorEntity[GoCardlessDataUpdateCoordinator]):
    """Base coordinator entity with shared account access helpers."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GoCardlessDataUpdateCoordinator, account_id: str) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self._account_id = account_id

    @property
    def account(self) -> AccountSnapshot | None:
        """Return current account snapshot."""
        snapshot = self.coordinator.data
        if snapshot is None:
            return None
        return snapshot.accounts.get(self._account_id)

    @property
    def available(self) -> bool:
        """Entity stays available when cached account exists."""
        return self.account is not None
