# Tasks

## 1. Route and handler

- [ ] 1.1 Add the `GET /health` route and verify it appears in the router table.
- [ ] 1.2 Implement the ready response and verify `GET /health` returns `200` with `{"status":"ok"}`.
- [ ] 1.3 Implement the unavailable response and verify a missing required dependency returns `503` with `{"status":"unavailable"}`.

## 2. Tests and documentation

- [ ] 2.1 Add handler tests for the ready and unavailable scenarios and verify the test suite passes.
- [ ] 2.2 Document the endpoint in the API reference and verify the documented request returns the expected response.
- [ ] 2.3 Run `./init.sh` and record the result in `feature_list.json` evidence.
