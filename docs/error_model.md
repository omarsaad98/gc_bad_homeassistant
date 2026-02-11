# Error Model

## API Layer Exceptions

The API client raises explicit exceptions:

- `GCBadCannotConnectError`: transport/network failure
- `GCBadRateLimitError`: local rate limit policy blocked request
- `GCBadResponseError`: payload schema does not match expected shape
- `GCBadApiError`: generic API/auth failure parent

## Coordinator Handling

- Network and rate-limit failures are raised as `UpdateFailed`.
- Authentication failures are raised as `ConfigEntryAuthFailed`.
- Cached snapshot remains available to entities even after update failure.

## Config Flow Handling

- Invalid credentials -> `invalid_auth`
- API unreachable -> `cannot_connect`
- Unexpected flow exception -> `unknown`

## Options Flow Handling

- Missing state -> `missing_configuration`
- Requisition create/verify failure -> `requisition_failed`
- Requisition still pending authorization -> `authorization_pending`
- Requisition terminal failure -> `authorization_failed`
