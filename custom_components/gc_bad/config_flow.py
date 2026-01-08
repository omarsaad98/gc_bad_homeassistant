"""Config flow for GoCardless Bank Account Data integration."""
from __future__ import annotations

import logging
from typing import Any

import pycountry
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api_client import GoCardlessAPIClient
from .const import CONF_SECRET_ID, CONF_SECRET_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_countries() -> dict[str, str]:
    """Get dictionary of country codes and names from pycountry."""
    return {country.alpha_2: country.name for country in pycountry.countries}


class GoCardlessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GoCardless Bank Account Data."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_client: GoCardlessAPIClient | None = None
        self._country: str | None = None
        self._institutions: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            secret_id = user_input[CONF_SECRET_ID]
            secret_key = user_input[CONF_SECRET_KEY]
            
            # Validate the credentials
            api_client = GoCardlessAPIClient(self.hass, secret_id, secret_key)
            
            try:
                if await api_client.validate_api_key():
                    # Check if already configured
                    await self.async_set_unique_id(secret_id)
                    self._abort_if_unique_id_configured()
                    
                    return self.async_create_entry(
                        title="GoCardless Bank Account Data",
                        data={
                            CONF_SECRET_ID: secret_id,
                            CONF_SECRET_KEY: secret_key,
                        },
                    )
                else:
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
    ) -> GoCardlessOptionsFlowHandler:
        """Get the options flow for this handler."""
        return GoCardlessOptionsFlowHandler(config_entry)


class GoCardlessOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for adding new bank connections."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self._api_client: GoCardlessAPIClient | None = None
        self._country: str | None = None
        self._institutions: list[dict[str, Any]] = []
        self._selected_institution: dict[str, Any] | None = None
        self._requisition_id: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            if user_input.get("add_requisition"):
                return await self.async_step_select_country()
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional("add_requisition", default=False): bool,
                }
            ),
        )

    async def async_step_select_country(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select country for bank."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._country = user_input["country"]
            
            # Get API client
            secret_id = self.config_entry.data[CONF_SECRET_ID]
            secret_key = self.config_entry.data[CONF_SECRET_KEY]
            self._api_client = GoCardlessAPIClient(self.hass, secret_id, secret_key)
            
            # Fetch institutions for selected country
            try:
                self._institutions = await self._api_client.get_institutions(
                    self._country
                )
                if self._institutions:
                    return await self.async_step_select_institution()
                else:
                    errors["base"] = "no_institutions"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Failed to fetch institutions")
                errors["base"] = "cannot_connect"

        # Preserve the selected country when re-displaying the form
        data = {}
        if self._country is not None:
            data["country"] = self._country

        return self.async_show_form(
            step_id="select_country",
            data_schema=vol.Schema(
                {
                    vol.Required("country"): vol.In(get_countries()),
                }
            ),
            data=data,
            errors=errors,
        )

    async def async_step_select_institution(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select institution (bank)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            institution_id = user_input["institution_id"]
            
            # Find the selected institution
            self._selected_institution = next(
                (inst for inst in self._institutions if inst["id"] == institution_id),
                None,
            )
            
            if self._selected_institution:
                # Ensure API client is initialized
                if self._api_client is None:
                    secret_id = self.config_entry.data[CONF_SECRET_ID]
                    secret_key = self.config_entry.data[CONF_SECRET_KEY]
                    self._api_client = GoCardlessAPIClient(self.hass, secret_id, secret_key)
                
                try:
                    result = await self.async_step_authorize()
                    # Check if result is an abort (dict with "type" key equal to "abort")
                    if isinstance(result, dict) and result.get("type") == "abort":
                        reason = result.get("reason", "requisition_failed")
                        _LOGGER.error(
                            "Authorization aborted for institution %s: %s",
                            institution_id,
                            reason,
                        )
                        # Map abort reasons to error keys (only requisition_failed is in both)
                        if reason == "requisition_failed":
                            errors["base"] = "requisition_failed"
                        else:
                            # For other abort reasons, use a generic error
                            errors["base"] = "requisition_failed"
                    else:
                        return result
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Failed to start authorization for institution %s", institution_id)
                    errors["base"] = "requisition_failed"
            else:
                errors["base"] = "invalid_institution"

        # Ensure institutions are loaded
        if not self._institutions:
            _LOGGER.error("No institutions available for selection")
            if not errors:
                errors["base"] = "no_institutions"
        
        # Create institution choices (empty dict if no institutions)
        institution_choices = {
            inst["id"]: inst["name"] for inst in self._institutions
        } if self._institutions else {}

        return self.async_show_form(
            step_id="select_institution",
            data_schema=vol.Schema(
                {
                    vol.Required("institution_id"): vol.In(institution_choices),
                }
            ),
            errors=errors,
        )

    async def async_step_authorize(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Start OAuth authorization flow."""
        if self._api_client is None or self._selected_institution is None:
            return self.async_abort(reason="missing_configuration")

        # Build callback URL with flow_id so we can complete the right flow
        # when the user returns from GoCardless
        try:
            # Use external_url if available, otherwise fall back to internal_url
            base_url = self.hass.config.external_url or self.hass.config.internal_url
            if not base_url:
                _LOGGER.error("Home Assistant base URL is not configured (neither external_url nor internal_url)")
                return self.async_abort(reason="missing_configuration")
            
            redirect_url = (
                f"{base_url}/api/gc_bad/callback"
                f"?flow_id={self.flow_id}"
            )
            _LOGGER.debug("Using redirect URL: %s", redirect_url)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Failed to build redirect URL: %s", err)
            return self.async_abort(reason="missing_configuration")
        
        try:
            requisition = await self._api_client.create_requisition(
                institution_id=self._selected_institution["id"],
                redirect_url=redirect_url,
                reference=f"ha_{self.config_entry.entry_id}",
            )
            
            if requisition and "link" in requisition and "id" in requisition:
                # Store requisition ID for later verification
                self._requisition_id = requisition["id"]
                
                # Also store in flow context to persist across flow resumptions
                if not hasattr(self, "_flow_context"):
                    self._flow_context = {}
                self._flow_context["requisition_id"] = requisition["id"]
                
                _LOGGER.info(
                    "Created requisition %s for institution %s",
                    self._requisition_id,
                    self._selected_institution["name"],
                )
                
                # Return external step to redirect user to bank authorization
                return self.async_external_step(
                    step_id="authorize",
                    url=requisition["link"],
                )
            else:
                _LOGGER.error(
                    "Invalid requisition response: missing 'link' or 'id'. Response: %s",
                    requisition,
                )
                return self.async_abort(reason="requisition_failed")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Failed to create requisition")
            return self.async_abort(reason="requisition_failed")

    async def async_step_authorize_complete(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Complete the authorization after user returns from bank."""
        # Restore requisition_id from flow context if instance variable is lost
        if self._requisition_id is None and hasattr(self, "_flow_context"):
            self._requisition_id = self._flow_context.get("requisition_id")
        
        # Ensure API client is initialized
        if self._api_client is None:
            secret_id = self.config_entry.data[CONF_SECRET_ID]
            secret_key = self.config_entry.data[CONF_SECRET_KEY]
            self._api_client = GoCardlessAPIClient(self.hass, secret_id, secret_key)
        
        if self._requisition_id is None:
            _LOGGER.error("Requisition ID not found in flow context")
            return self.async_abort(reason="missing_configuration")
        
        # Verify the requisition was successfully authorized
        try:
            requisition = await self._api_client.get_requisition(self._requisition_id)
            
            if not requisition:
                _LOGGER.error(
                    "Could not retrieve requisition %s", self._requisition_id
                )
                return self.async_abort(reason="requisition_failed")
            
            status = requisition.get("status")
            
            if status == "LN":  # Linked - successfully authorized
                _LOGGER.info(
                    "Requisition %s successfully linked", self._requisition_id
                )
                # Trigger a coordinator update to fetch the new accounts
                return self.async_create_entry(
                    title="",
                    data={"requisition_id": self._requisition_id},
                )
            elif status in ["CR", "UA"]:  # Created or Under Authorization
                _LOGGER.warning(
                    "Requisition %s is still being authorized (status: %s)",
                    self._requisition_id,
                    status,
                )
                return self.async_abort(reason="authorization_pending")
            else:
                _LOGGER.error(
                    "Requisition %s has unexpected status: %s",
                    self._requisition_id,
                    status,
                )
                return self.async_abort(reason="authorization_failed")
                
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception(
                "Failed to verify requisition %s", self._requisition_id
            )
            return self.async_abort(reason="requisition_failed")

