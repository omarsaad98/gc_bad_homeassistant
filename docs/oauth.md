# OAuth & Bank Connections

## Overview
The GoCardless Bank Account Data API uses a "Requisition" based flow for connecting to banks. This integration implements a secure, user-friendly OAuth2 flow within Home Assistant.

## Connection Flow
1. **Initiation**: User selects "Add New Bank Connection" in the integration options.
2. **Selection**: User chooses their country and then their specific bank from a list.
3. **Requisition Creation**: The integration creates a requisition with GoCardless and generates a unique `flow_id`.
4. **Redirection**: User is redirected to the GoCardless/Bank authorization page.
5. **Authorization**: User grants permission at their bank.
6. **Callback**: The bank redirects the user back to Home Assistant's internal callback endpoint: `/api/gc_bad/callback?flow_id=...`.
7. **Verification**: The integration verifies the requisition status is "LN" (Linked) and completes the setup.

## Callback Handler
The callback handler is a custom `HomeAssistantView` registered at startup. It provides:
- **Security**: Uses a temporary, single-use `flow_id` to track and complete the specific configuration flow.
- **User Feedback**: Displays a professional success or error page upon return.
- **Automation**: Signals the config flow to advance automatically once authorization is detected.

## Requirements for Production
For the OAuth flow to work in production:
- **HTTPS**: Your Home Assistant instance must be accessible via HTTPS.
- **External URL**: The `external_url` must be correctly configured in Home Assistant's general settings.
- **GoCardless Redirect**: The redirect URL provided to GoCardless must match your external HA URL.

## Requisition Statuses
The integration monitors several statuses:
- `CR`: Created
- `LN`: Linked (Success)
- `EX`: Expired
- `UA`: Undergoing Authorization
- `RJ`: Rejected

