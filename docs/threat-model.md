# Threat model

## Protected assets

- `CHILE_PUBLIC_MARKET_TICKET`
- The external daily request budget
- Integrity and provenance of procurement results
- The host process and local filesystem

## Initial controls

- The ticket is accepted only through the server environment.
- Tools never accept or return credentials.
- The MVP exposes no shell, filesystem-write or destructive operation.
- Inputs and result limits are validated by Pydantic.
- Demo data is visibly marked and cannot be confused with official data.
- The default mode makes no network calls.
- Live calls reserve request budget atomically before reaching the upstream SDK.
- Cache entries have bounded TTLs and contain no credentials.
- The API timeout is bounded and configurable from 1 to 120 seconds.
- Compra Ágil contract tests use secret-free fixtures based on observed production responses.
- The data-source diagnostic reports readiness without returning the ticket.

## Planned controls for live mode

- Redacted structured logs and correlation IDs
- Per-operation metrics and cache-hit telemetry
- Bounded retries with backoff
- Opt-in live tests outside pull requests
