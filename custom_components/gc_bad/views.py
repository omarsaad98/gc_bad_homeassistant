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
        # Get the flow_id from the query (we added it to the redirect URL)
        flow_id = request.query.get("flow_id")
        # GoCardless may also send a 'ref' parameter with the requisition reference
        requisition_ref = request.query.get("ref")
        
        _LOGGER.info(
            "Received OAuth callback - flow_id: %s, ref: %s, all params: %s",
            flow_id,
            requisition_ref,
            dict(request.query),
        )
        
        if not flow_id:
            _LOGGER.error("No flow ID in callback URL. Query params: %s", dict(request.query))
            return self._error_response("Missing flow ID in callback URL")
        
        try:
            # Get the flow to verify it exists
            flow = await self.hass.config_entries.flow.async_get(flow_id)
            if flow is None:
                _LOGGER.error("Flow %s not found - may have expired", flow_id)
                return self._error_response("Flow not found or expired. Please try again.")
            
            _LOGGER.info("Resuming flow %s (type: %s, handler: %s)", flow_id, type(flow).__name__, flow.handler)
            
            # Resume the flow - this should trigger async_step_authorize_complete
            # When using async_external_step, resuming the flow automatically calls the _complete step
            result = await self.hass.config_entries.flow.async_configure(
                flow_id=flow_id,
                user_input={},
            )
            
            _LOGGER.info("Flow resume completed. Result type: %s", result.get("type") if isinstance(result, dict) else type(result))
            
        except Exception as err:
            _LOGGER.exception("Failed to complete config flow: %s", err)
            return self._error_response(f"Failed to complete authorization: {str(err)}")
        
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

