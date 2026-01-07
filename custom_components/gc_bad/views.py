"""Views for GoCardless Bank Account Data integration."""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)


class GoCardlessAuthCallbackView(HomeAssistantView):
    """Handle GoCardless OAuth callback."""

    requires_auth = False
    url = "/api/gc_bad/callback"
    name = "api:gc_bad:callback"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the callback view."""
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        """Handle callback from GoCardless after bank authorization.
        
        GoCardless redirects here after user completes bank authorization.
        The URL will contain query parameters with requisition info.
        """
        # Get the reference parameter (our flow_id) from the query
        flow_id = request.query.get("flow_id")
        requisition_id = request.query.get("ref")
        
        if not flow_id:
            _LOGGER.error("No flow ID in callback")
            return self._error_response("Missing flow ID")
        
        _LOGGER.info(
            "Received OAuth callback for flow %s (requisition: %s)",
            flow_id,
            requisition_id,
        )
        
        try:
            # Signal the config flow that authorization is complete
            await self.hass.config_entries.flow.async_configure(
                flow_id=flow_id,
                user_input={},
            )
        except Exception as err:
            _LOGGER.error("Failed to complete config flow: %s", err)
            return self._error_response(str(err))
        
        return self._success_response()
    
    def _success_response(self) -> web.Response:
        """Return a success HTML page."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>GoCardless Authorization Complete</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                }
                h1 {
                    color: #03a9f4;
                    margin-bottom: 20px;
                }
                p {
                    color: #666;
                    line-height: 1.6;
                }
                .success {
                    font-size: 48px;
                    margin-bottom: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✓</div>
                <h1>Authorization Complete!</h1>
                <p>Your bank account has been successfully connected to Home Assistant.</p>
                <p>You can close this window and return to Home Assistant.</p>
            </div>
            <script>
                // Auto-close after 3 seconds if opened in a popup
                setTimeout(function() {
                    if (window.opener) {
                        window.close();
                    }
                }, 3000);
            </script>
        </body>
        </html>
        """
        
        return web.Response(text=html, content_type="text/html")
    
    def _error_response(self, error: str) -> web.Response:
        """Return an error HTML page."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>GoCardless Authorization Error</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                }}
                h1 {{
                    color: #f44336;
                    margin-bottom: 20px;
                }}
                p {{
                    color: #666;
                    line-height: 1.6;
                }}
                .error {{
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
                .error-details {{
                    background: #ffebee;
                    padding: 10px;
                    border-radius: 4px;
                    margin-top: 20px;
                    font-family: monospace;
                    font-size: 12px;
                    color: #c62828;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">✗</div>
                <h1>Authorization Error</h1>
                <p>There was a problem completing the bank authorization.</p>
                <p>Please return to Home Assistant and try again.</p>
                <div class="error-details">{error}</div>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html", status=400)

