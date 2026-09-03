# Architecture

ProcuraCL treats MCP as an interface, not as the application architecture.

```text
MCP host
  -> MCP tools, resource and prompt
  -> OpportunityService / WatchlistService
  -> MarketGateway protocol
  -> read-through SQLite cache (live mode)
  -> atomic daily request budget (live mode)
  -> demo adapter / live adapters
       -> typed community SDK for legacy Mercado Público v1
       -> local anti-corruption client for Compra Ágil v2
  -> Mercado Público and Compra Ágil APIs

WatchlistService
  -> SQLite watchlists, snapshots and sync runs
```

The domain layer owns normalized models. The application layer owns use cases. Infrastructure
adapters translate external contracts. This keeps a future FastAPI interface, persistence layer or
background sync worker from duplicating business logic.

## Synchronization semantics

A watchlist search deduplicates opportunities by upstream code. Each normalized opportunity is
fingerprinted without `retrieved_at`. The first observation is `new`, a different fingerprint is
`updated`, and an identical fingerprint is `unchanged`. Unchanged observations update `last_seen_at`
without generating a duplicate change event.

## Request path in live mode

The cache is outside the budget wrapper. A hit returns locally. A miss reserves one request in an
SQLite `BEGIN IMMEDIATE` transaction before the upstream call, preventing concurrent processes from
overspending the configured local limit.

Compra Ágil is parsed through a small local model that ignores unknown fields and accepts the
document identifiers currently returned by the official API. This isolates the application from
contract drift in the v2 service and from release timing in third-party packages. Secret-free
fixtures preserve the observed production response shape in unit tests.

## Data provenance

Every opportunity includes `source` and `retrieved_at`. Synthetic records are always labeled
`demo`. Live results must use `mercado_publico` and preserve the upstream operation code.
