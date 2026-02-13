"""Config flow for GoCardless Bank Account Data integration."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import pycountry
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api.client import GCBadApiError, GCBadCannotConnectError, GoCardlessApiClient
from .const import CONF_SECRET_ID, CONF_SECRET_KEY, DOMAIN, IGNORED_INSTITUTION_PREFIXES
from .storage import IntegrationStorage

_LOGGER = logging.getLogger(__name__)


def get_countries() -> dict[str, str]:
    """Return all countries as code->name mapping."""
    return {country.alpha_2: country.name for country in pycountry.countries}


class GoCardlessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for credentials setup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            secret_id = user_input[CONF_SECRET_ID]
            secret_key = user_input[CONF_SECRET_KEY]
            storage = IntegrationStorage(self.hass, f"validate_{secret_id[:8]}")
            client = GoCardlessApiClient(self.hass, storage, secret_id, secret_key)
            try:
                if not await client.validate_api_key():
                    errors["base"] = "invalid_auth"
                else:
                    await self.async_set_unique_id(secret_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="GoCardless Bank Account Data",
                        data={
                            CONF_SECRET_ID: secret_id,
                            CONF_SECRET_KEY: secret_key,
                        },
                    )
            except GCBadCannotConnectError:
                errors["base"] = "cannot_connect"
            except GCBadApiError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during authentication")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SECRET_ID): str,
                    vol.Required(CONF_SECRET_KEY): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "GoCardlessOptionsFlowHandler":
        """Return options flow handler."""
        return GoCardlessOptionsFlowHandler(config_entry)


class GoCardlessOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for adding bank requisitions."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow state."""
        super().__init__()
        self._state: dict[str, Any] = {
            "country": None,
            "institutions": [],
            "institution_id": None,
            "requisition_id": None,
        }
        self._client: GoCardlessApiClient | None = None

    def _get_client(self) -> GoCardlessApiClient:
        """Create client lazily for options flow."""
        if self._client is None:
            storage = IntegrationStorage(self.hass, self.config_entry.entry_id)
            self._client = GoCardlessApiClient(
                self.hass,
                storage,
                self.config_entry.data[CONF_SECRET_ID],
                self.config_entry.data[CONF_SECRET_KEY],
            )
        return self._client

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Present options root step."""
        if user_input and user_input.get("add_requisition"):
            return await self.async_step_select_country()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Optional("add_requisition", default=False): bool}),
        )

    async def async_step_select_country(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select country and load institutions."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._state["country"] = user_input["country"]
            try:
                institutions = await self._get_client().get_institutions(self._state["country"])
                if institutions:
                    institutions = [
                        inst
                        for inst in institutions
                        if not inst.get("id", "").startswith(IGNORED_INSTITUTION_PREFIXES)
                    ]
            except GCBadCannotConnectError:
                errors["base"] = "cannot_connect"
            except GCBadApiError:
                errors["base"] = "cannot_connect"
            else:
                if not institutions:
                    errors["base"] = "no_institutions"
                else:
                    self._state["institutions"] = institutions
                    return await self.async_step_select_institution()

        default_country = self._state["country"] or vol.UNDEFINED
        return self.async_show_form(
            step_id="select_country",
            data_schema=vol.Schema(
                {vol.Required("country", default=default_country): vol.In(get_countries())}
            ),
            errors=errors,
        )

    async def async_step_select_institution(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Select institution to authorize."""
        errors: dict[str, str] = {}
        institutions = self._state["institutions"]
        choices = {item["id"]: item["name"] for item in institutions if "id" in item}

        if user_input is not None:
            institution_id = user_input["institution_id"]
            if institution_id not in choices:
                errors["base"] = "invalid_institution"
            else:
                self._state["institution_id"] = institution_id
                return await self.async_step_authorize()

        return self.async_show_form(
            step_id="select_institution",
            data_schema=vol.Schema({vol.Required("institution_id"): vol.In(choices)}),
            errors=errors,
        )

    async def async_step_authorize(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Create requisition and redirect user to bank authorization."""
        institution_id = self._state["institution_id"]
        if not institution_id:
            return self.async_abort(reason="missing_configuration")

        base_url = self.hass.config.external_url or self.hass.config.internal_url
        if not base_url:
            return self.async_abort(reason="missing_configuration")

        redirect_url = f"{base_url}/api/gc_bad/callback?flow_id={self.flow_id}"
        reference = f"ha_{self.config_entry.entry_id}_{uuid.uuid4().hex[:8]}"
        try:
            requisition = await self._get_client().create_requisition(
                institution_id=institution_id,
                redirect_url=redirect_url,
                reference=reference,
            )
        except GCBadApiError:
            return self.async_abort(reason="requisition_failed")

        link = requisition.get("link")
        requisition_id = requisition.get("id")
        if not link or not requisition_id:
            return self.async_abort(reason="requisition_failed")

        self._state["requisition_id"] = requisition_id
        return self.async_external_step(step_id="authorize", url=link)

    async def async_step_authorize_complete(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Complete authorization and persist options."""
        requisition_id = self._state["requisition_id"]
        if not requisition_id:
            return self.async_abort(reason="missing_configuration")

        try:
            requisition = await self._get_client().get_requisition(requisition_id)
        except GCBadApiError:
            return self.async_abort(reason="requisition_failed")

        status = requisition.get("status")
        if status == "LN":
            previous = self.config_entry.options.get("requisition_ids", [])
            merged = sorted(set(previous + [requisition_id]))
            return self.async_create_entry(
                title="",
                data={"requisition_ids": merged},
            )
        if status in {"CR", "UA"}:
            return self.async_abort(reason="authorization_pending")
        return self.async_abort(reason="authorization_failed")

