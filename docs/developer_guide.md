# Developer Guide

## Add a New Sensor Type

1. Add required fields to typed models in `custom_components/gc_bad/models.py`.
2. Populate those fields in `custom_components/gc_bad/coordinator.py`.
3. Add/extend entity implementation in `custom_components/gc_bad/sensor.py`.
4. Add unit tests for projection behavior in `tests/test_sensor.py`.

## Change API Behavior

1. Keep endpoint contract logic in `custom_components/gc_bad/api/client.py`.
2. Keep token lifecycle concerns in `custom_components/gc_bad/api/auth.py`.
3. Keep rate-limit behavior in `custom_components/gc_bad/api/rate_limits.py`.
4. Avoid adding API logic to coordinator entities or config flow.

## Change Persistence Schema

1. Modify `custom_components/gc_bad/storage.py`.
2. Bump `STORAGE_VERSION` in `custom_components/gc_bad/const.py`.
3. Keep migrations and compatibility local to storage helpers.

## Testing Expectations

- Unit tests are default and fast.
- Live tests are optional and marked with `@pytest.mark.live`.
- Config flow, coordinator, and sensor behavior should have direct test coverage.
